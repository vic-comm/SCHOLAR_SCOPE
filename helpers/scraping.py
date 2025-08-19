# latest to be used
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from datetime import datetime
import re
import time
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
from decouple import config
import json
import time
import re
from urllib.parse import urljoin, urlparse
import os
from datetime import datetime
# Remove the decouple import since we're not using environment variables
# from decouple import config

class ScholarshipSeleniumScraper:
    def __init__(self, chrome_driver_path=None):
        self.driver = None
        self.chrome_driver_path = chrome_driver_path  # Optional: specify chromedriver path
        
    def connect_browser(self):
        """Connect to local Chrome browser"""
        print('Starting local Chrome browser...')
        
        # Set up Chrome options
        options = ChromeOptions()
        
        # Add options to avoid detection and improve performance
        options.add_argument('--no-sandbox')
        options.add_argument('--headless')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Optional: Run in headless mode (uncomment if you don't want to see the browser)
        # options.add_argument('--headless')
        
        # Optional: Set window size
        options.add_argument('--window-size=1920,1080')
        
        try:
            # Method 1: If you have chromedriver in your PATH or specified path
            if self.chrome_driver_path:
                service = Service(self.chrome_driver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                # Method 2: Let Selenium manage chromedriver automatically (Selenium 4.6+)
                self.driver = webdriver.Chrome(options=options)
                
            # Execute script to hide webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            print('Chrome browser started successfully!')
            
        except Exception as e:
            print(f"Error starting Chrome browser: {str(e)}")
            print("\nTroubleshooting tips:")
            print("1. Make sure Chrome browser is installed")
            print("2. Install/update chromedriver: pip install --upgrade chromedriver-autoinstaller")
            print("3. Or manually download chromedriver from https://chromedriver.chromium.org/")
            raise
    
        
    def scrape_scholarship_data(self, url):
        """Scrape scholarship data optimized for Django model"""
        try:
            self.connect_browser()
            
            print(f'Navigating to {url}...')
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Extract data matching Django model fields
            scholarship_data = {
                'title': self.extract_title(),
                'description': self.extract_description(),
                'reward': self.extract_reward(),
                'link': self.extract_application_link(),
                'start_date': self.extract_start_date(),
                'end_date': self.extract_end_date(),
                'requirements': self.extract_requirements(),
                'eligibility': self.extract_eligibility(),
                'tags': self.extract_tags(),
                # 'active': self.determine_if_active(),
                'scraped_at': datetime.now().isoformat()
            }
            
            print('Data extraction completed!')
            return scholarship_data
            
        except Exception as e:
            print(f"Error during scraping: {str(e)}")
            return None
        finally:
            if self.driver:
                self.driver.quit()
                print('Browser connection closed.')
     
    def extract_application_link(self):
        """Extract application link"""
        try:
            # Look for application buttons/links
            app_selectors = [
                "a[href*='apply']",
                "a[href*='application']",
                "button[onclick*='apply']",
                "a:contains('Apply')",
                "a:contains('Submit')",
                ".apply-btn",
                ".application-link"
            ]
            
            for selector in app_selectors:
                try:
                    if ':contains(' in selector:
                        # Use XPath for text-based selection
                        xpath = f"//a[contains(text(), '{selector.split(':contains(')[1].split(')')[0].strip("'")}')]"
                        elements = self.driver.find_elements(By.XPATH, xpath)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    if elements:
                        element = elements[0]
                        return {
                            'text': element.text.strip(),
                            'url': element.get_attribute('href') or element.get_attribute('onclick')
                        }
                except:
                    continue
            
            # Look for forms with application-related action
            forms = self.driver.find_elements(By.TAG_NAME, "form")
            for form in forms:
                action = form.get_attribute('action')
                if action and any(keyword in action.lower() for keyword in ['apply', 'application', 'submit']):
                    return {
                        'text': 'Application form',
                        'url': action
                    }
            
        except Exception as e:
            print(f"Error extracting application link: {e}")
        
        return "Application link not found"
    
    
    def extract_title(self):
        """Extract scholarship title"""
        selectors = [
            "h1",
            ".entry-title", 
            ".post-title",
            ".scholarship-title",
            "[class*='title']"
        ]
        
        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                title = element.text.strip()
                if title and len(title) > 5:
                    # Clean up title
                    title = title.split('|')[0].strip()
                    title = title.split(' - ')[0].strip()
                    return title[:255]  # Match Django CharField max_length
            except NoSuchElementException:
                continue
        
        # Fallback to page title
        try:
            return self.driver.title.split('|')[0].strip()[:255]
        except:
            return "Scholarship Title Not Found"

    def extract_description(self):
        """Extract scholarship description"""
        description_parts = []
        
        # Strategy 1: Meta description
        try:
            meta_desc = self.driver.find_element(By.CSS_SELECTOR, 'meta[name="description"]')
            content = meta_desc.get_attribute('content')
            if content and len(content) > 50:
                description_parts.append(content.strip())
        except:
            pass
        
        # Strategy 2: First few paragraphs
        try:
            paragraphs = self.driver.find_elements(By.CSS_SELECTOR, "p")
            content_paragraphs = []
            for p in paragraphs[:5]:
                text = p.text.strip()
                if len(text) > 50:
                    # Skip navigation/footer text
                    skip_words = ['home', 'menu', 'navigation', 'copyright', 'privacy', 'cookie']
                    if not any(skip_word in text.lower() for skip_word in skip_words):
                        content_paragraphs.append(text)
                        if len(content_paragraphs) >= 2:
                            break
            
            description_parts.extend(content_paragraphs)
        except:
            pass
        
        # Strategy 3: Article content
        try:
            article_selectors = ['.entry-content', '.post-content', '.article-content', 'article']
            for selector in article_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    text = element.text.strip()
                    if len(text) > 100:
                        description_parts.append(text[:500])
                        break
                except:
                    continue
        except:
            pass
        
        if description_parts:
            description = ' '.join(description_parts)
            description = re.sub(r'\s+', ' ', description)  # Clean whitespace
            return description
        
        return "No description available"

    def extract_reward(self):
        """Extract scholarship reward/amount"""
        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            # Nigerian Naira patterns
            naira_patterns = [
                r'₦\s*([0-9,]+(?:\.[0-9]{2})?)',
                r'N\s*([0-9,]+(?:\.[0-9]{2})?)',
                r'([0-9,]+(?:\.[0-9]{2})?)\s*naira'
            ]
            
            # USD patterns  
            usd_patterns = [
                r'\$\s*([0-9,]+(?:\.[0-9]{2})?)',
                r'([0-9,]+(?:\.[0-9]{2})?)\s*(?:USD|dollars?)'
            ]
            
            # General patterns
            general_patterns = [
                r'worth\s*(?:of\s*)?₦?\$?\s*([0-9,]+)',
                r'value\s*(?:of\s*)?₦?\$?\s*([0-9,]+)',
                r'amount\s*(?:of\s*)?₦?\$?\s*([0-9,]+)'
            ]
            
            all_patterns = naira_patterns + usd_patterns + general_patterns
            
            for pattern in all_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    for match in matches:
                        if isinstance(match, tuple):
                            match = match[0]
                        try:
                            num_value = float(match.replace(',', ''))
                            if num_value > 1000:  # Reasonable minimum
                                return f"₦{match}" if any(p in pattern for p in naira_patterns) else f"${match}"
                        except:
                            continue
            
            # Look for non-monetary rewards
            reward_keywords = ['tuition', 'allowance', 'stipend', 'support', 'funding', 'full scholarship']
            for keyword in reward_keywords:
                if keyword in page_text.lower():
                    return f"Educational {keyword}"
            
            return "Amount not specified"
            
        except:
            return "Amount not specified"

    def extract_start_date(self):
        """Extract application start date/opening date"""
        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            # Look for start date patterns
            start_patterns = [
                r'application\s*(?:opens?|starts?)[:\s]*([^.!?\n]+)',
                r'opening\s*date[:\s]*([^.!?\n]+)',
                r'start\s*date[:\s]*([^.!?\n]+)',
                r'begins?[:\s]*([^.!?\n]+)',
                r'from[:\s]*([^.!?\n]+?)(?:\s*to\s*|\s*-\s*)',
                r'available\s*from[:\s]*([^.!?\n]+)',
                r'registration\s*(?:opens?|starts?)[:\s]*([^.!?\n]+)'
            ]
            
            for pattern in start_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    date_text = matches[0].strip()
                    parsed_date = self.parse_date_string(date_text)
                    if parsed_date:
                        return parsed_date.isoformat()
            
            return None
            
        except:
            return None

    def extract_end_date(self):
        """Extract application deadline/end date"""
        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            # Look for deadline patterns
            deadline_patterns = [
                r'deadline[:\s]*([^.!?\n]+)',
                r'due date[:\s]*([^.!?\n]+)',
                r'closing date[:\s]*([^.!?\n]+)',
                r'last date[:\s]*([^.!?\n]+)',
                r'application closes[:\s]*([^.!?\n]+)',
                r'expires?[:\s]*([^.!?\n]+)',
                r'until[:\s]*([^.!?\n]+)',
                r'by[:\s]*([^.!?\n]+)'
            ]
            
            for pattern in deadline_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    date_text = matches[0].strip()
                    parsed_date = self.parse_date_string(date_text)
                    if parsed_date:
                        return parsed_date.isoformat()
            
            return None
            
        except:
            return None

    def extract_requirements(self):
        """Extract scholarship requirements/documents needed"""
        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            requirements = []
            
            # Look for requirement sections
            requirement_patterns = [
                r'requirements?[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                r'documents?\s*(?:required|needed)[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                r'application\s*requirements?[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                r'needed\s*documents?[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                r'submit[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                r'must\s*(?:provide|submit|include)[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)'
            ]
            
            # Try to find structured requirement lists
            try:
                # Look for list elements that might contain requirements
                list_selectors = [
                    'ul li', 'ol li', '.requirements li', '.documents li',
                    '[class*="requirement"] li', '[class*="document"] li'
                ]
                
                for selector in list_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            text = element.text.strip()
                            if self.is_requirement_text(text):
                                requirements.append(text)
                                if len(requirements) >= 10:  # Limit to 10 requirements
                                    break
                        if requirements:
                            break
                    except:
                        continue
            except:
                pass
            
            # If no structured lists found, use pattern matching
            if not requirements:
                for pattern in requirement_patterns:
                    matches = re.findall(pattern, page_text, re.IGNORECASE | re.MULTILINE)
                    if matches:
                        requirement_text = matches[0].strip()
                        # Split into individual requirements
                        req_lines = self.parse_requirement_text(requirement_text)
                        requirements.extend(req_lines)
                        if requirements:
                            break
            
            # Look for common requirement keywords if nothing found
            if not requirements:
                common_requirements = self.extract_common_requirements(page_text)
                requirements.extend(common_requirements)
            
            # Clean and format requirements
            cleaned_requirements = []
            for req in requirements[:10]:  # Limit to 10 requirements
                req = req.strip()
                if len(req) > 10 and len(req) < 200:  # Reasonable length
                    # Remove bullet points and numbering
                    req = re.sub(r'^[\d\.\)\-\*\•\►\→\➤]\s*', '', req)
                    req = re.sub(r'^\w\)\s*', '', req)  # Remove a), b), etc.
                    cleaned_requirements.append(req.strip())
            
            return cleaned_requirements if cleaned_requirements else ["Requirements not specified"]
            
        except Exception as e:
            print(f"Error extracting requirements: {str(e)}")
            return ["Requirements not specified"]
    

    def extract_eligibility(self):
        """Extract scholarship eligibility criteria"""
        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            eligibility = []
            
            # Look for eligibility sections
            eligibility_patterns = [
                r'eligibility[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                r'eligible\s*(?:candidates?|applicants?)[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                r'who\s*can\s*apply[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                r'criteria[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                r'qualifications?[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)',
                r'must\s*be[:\s]*([^.!?\n]*(?:\n[^.!?\n]*)*)'
            ]
            
            # Try to find structured eligibility lists
            try:
                # Look for list elements that might contain eligibility
                list_selectors = [
                    'ul li', 'ol li', '.eligibility li', '.criteria li',
                    '[class*="eligibility"] li', '[class*="criteria"] li',
                    '[class*="qualification"] li'
                ]
                
                for selector in list_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            text = element.text.strip()
                            if self.is_eligibility_text(text):
                                eligibility.append(text)
                                if len(eligibility) >= 10:  # Limit to 10 criteria
                                    break
                        if eligibility:
                            break
                    except:
                        continue
            except:
                pass
            
            # If no structured lists found, use pattern matching
            if not eligibility:
                for pattern in eligibility_patterns:
                    matches = re.findall(pattern, page_text, re.IGNORECASE | re.MULTILINE)
                    if matches:
                        eligibility_text = matches[0].strip()
                        # Split into individual criteria
                        eligibility_lines = self.parse_eligibility_text(eligibility_text)
                        eligibility.extend(eligibility_lines)
                        if eligibility:
                            break
            
            # Look for common eligibility keywords if nothing found
            if not eligibility:
                common_eligibility = self.extract_common_eligibility(page_text)
                eligibility.extend(common_eligibility)
            
            # Clean and format eligibility
            cleaned_eligibility = []
            for criteria in eligibility[:10]:  # Limit to 10 criteria
                criteria = criteria.strip()
                if len(criteria) > 10 and len(criteria) < 200:  # Reasonable length
                    # Remove bullet points and numbering
                    criteria = re.sub(r'^[\d\.\)\-\*\•\►\→\➤]\s*', '', criteria)
                    criteria = re.sub(r'^\w\)\s*', '', criteria)  # Remove a), b), etc.
                    cleaned_eligibility.append(criteria.strip())
            
            return cleaned_eligibility if cleaned_eligibility else ["Eligibility criteria not specified"]
            
        except Exception as e:
            print(f"Error extracting eligibility: {str(e)}")
            return ["Eligibility criteria not specified"]

    def is_requirement_text(self, text):
        """Check if text looks like a requirement"""
        requirement_keywords = [
            'transcript', 'certificate', 'cv', 'resume', 'letter', 'essay',
            'statement', 'recommendation', 'reference', 'passport', 'photo',
            'application form', 'birth certificate', 'identification',
            'academic record', 'degree', 'diploma', 'waec', 'jamb', 'ssce',
            'bank statement', 'financial', 'medical report', 'upload', 'submit'
        ]
        
        text_lower = text.lower()
        return (any(keyword in text_lower for keyword in requirement_keywords) and
                len(text) > 15 and len(text) < 200)

    def is_eligibility_text(self, text):
        """Check if text looks like eligibility criteria"""
        eligibility_keywords = [
            'citizen', 'age', 'year', 'grade', 'gpa', 'cgpa', 'score',
            'level', 'undergraduate', 'graduate', 'student', 'enrolled',
            'admitted', 'nationality', 'resident', 'income', 'family',
            'female', 'male', 'minority', 'disability', 'field of study',
            'department', 'faculty', 'university', 'college'
        ]
        
        text_lower = text.lower()
        return (any(keyword in text_lower for keyword in eligibility_keywords) and
                len(text) > 15 and len(text) < 200)

    def parse_requirement_text(self, text):
        """Parse requirement text into individual requirements"""
        requirements = []
        
        # Try splitting by common delimiters
        delimiters = ['\n', ';', '•', '►', '→', '➤']
        
        for delimiter in delimiters:
            if delimiter in text:
                parts = text.split(delimiter)
                for part in parts:
                    part = part.strip()
                    if self.is_requirement_text(part):
                        requirements.append(part)
                if requirements:
                    return requirements
        
        # If no clear delimiters, look for sentence patterns
        sentences = re.split(r'[.!?]', text)
        for sentence in sentences:
            sentence = sentence.strip()
            if self.is_requirement_text(sentence):
                requirements.append(sentence)
        
        return requirements if requirements else [text.strip()]

    def parse_eligibility_text(self, text):
        """Parse eligibility text into individual criteria"""
        eligibility = []
        
        # Try splitting by common delimiters
        delimiters = ['\n', ';', '•', '►', '→', '➤']
        
        for delimiter in delimiters:
            if delimiter in text:
                parts = text.split(delimiter)
                for part in parts:
                    part = part.strip()
                    if self.is_eligibility_text(part):
                        eligibility.append(part)
                if eligibility:
                    return eligibility
        
        # If no clear delimiters, look for sentence patterns
        sentences = re.split(r'[.!?]', text)
        for sentence in sentences:
            sentence = sentence.strip()
            if self.is_eligibility_text(sentence):
                eligibility.append(sentence)
        
        return eligibility if eligibility else [text.strip()]

    def extract_common_requirements(self, page_text):
        """Extract common requirement patterns from text"""
        requirements = []
        text_lower = page_text.lower()
        
        # Common document requirements
        document_patterns = {
            'Academic Transcript': ['transcript', 'academic record'],
            'CV/Resume': ['cv', 'resume', 'curriculum vitae'],
            'Passport Photograph': ['passport photo', 'recent photo'],
            'Birth Certificate': ['birth certificate'],
            'Letter of Recommendation': ['recommendation letter', 'reference letter'],
            'Statement of Purpose': ['statement of purpose', 'personal statement'],
            'Application Form': ['application form', 'completed form'],
            'Academic Certificates': ['certificate', 'degree certificate'],
            'Identification Document': ['id card', 'identification', 'national id']
        }
        
        for req_name, keywords in document_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                requirements.append(req_name)
        
        return requirements

    def extract_common_eligibility(self, page_text):
        """Extract common eligibility patterns from text"""
        eligibility = []
        text_lower = page_text.lower()
        
        # Age requirements
        age_match = re.search(r'(?:age|years?)\s*(?:between|from)?\s*(\d+)(?:\s*(?:to|and|-)\s*(\d+))?', text_lower)
        if age_match:
            if age_match.group(2):
                eligibility.append(f"Age between {age_match.group(1)} and {age_match.group(2)} years")
            else:
                eligibility.append(f"Age {age_match.group(1)} years or above")
        
        # Educational level
        if 'undergraduate' in text_lower:
            eligibility.append("Must be an undergraduate student")
        if 'graduate' in text_lower or 'postgraduate' in text_lower:
            eligibility.append("Must be a graduate/postgraduate student")
        
        # Nationality/Citizenship
        if 'nigerian' in text_lower and 'citizen' in text_lower:
            eligibility.append("Must be a Nigerian citizen")
        if 'international' in text_lower:
            eligibility.append("Open to international students")
        
        # Academic performance
        gpa_match = re.search(r'(?:gpa|cgpa)\s*(?:of\s*)?(\d+\.?\d*)', text_lower)
        if gpa_match:
            eligibility.append(f"Minimum GPA/CGPA of {gpa_match.group(1)}")
        
        # Gender requirements
        if 'female' in text_lower and 'only' in text_lower:
            eligibility.append("Female students only")
        if 'male' in text_lower and 'only' in text_lower:
            eligibility.append("Male students only")
        
        return eligibility
        """Extract tags/categories for the scholarship"""
        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            title_text = self.driver.title.lower()
            
            # Combine all text for analysis
            all_text = f"{page_text} {title_text}"
            
            tags = set()
            
            # Educational level tags
            level_keywords = {
                'undergraduate': ['undergraduate', 'bachelor', 'bsc', 'ba', 'first degree'],
                'postgraduate': ['postgraduate', 'masters', 'msc', 'ma', 'phd', 'doctorate'],
                'high school': ['secondary', 'high school', 'ssce', 'waec', 'neco'],
                'diploma': ['diploma', 'nd', 'hnd', 'certificate']
            }
            
            # Field of study tags
            field_keywords = {
                'engineering': ['engineering', 'engineer', 'technology'],
                'medicine': ['medicine', 'medical', 'health', 'nursing', 'pharmacy'],
                'law': ['law', 'legal', 'jurisprudence'],
                'business': ['business', 'management', 'mba', 'finance', 'accounting'],
                'science': ['science', 'biology', 'chemistry', 'physics', 'mathematics'],
                'arts': ['arts', 'literature', 'history', 'language'],
                'agriculture': ['agriculture', 'farming', 'veterinary'],
                'computer science': ['computer', 'software', 'programming', 'it', 'technology'],
                'education': ['education', 'teaching', 'pedagogy']
            }
            
            # Gender-based tags
            gender_keywords = {
                'female': ['women', 'female', 'girl', 'ladies'],
                'male': ['men', 'male', 'boy', 'gentleman']
            }
            
            # Location-based tags
            location_keywords = {
                'international': ['international', 'global', 'worldwide', 'abroad'],
                'nigeria': ['nigeria', 'nigerian', 'local'],
                'africa': ['africa', 'african'],
                'usa': ['usa', 'america', 'united states'],
                'uk': ['uk', 'britain', 'united kingdom'],
                'canada': ['canada', 'canadian']
            }
            
            # Special categories
            special_keywords = {
                'merit': ['merit', 'academic excellence', 'outstanding'],
                'need-based': ['need', 'financial aid', 'low income'],
                'minority': ['minority', 'disadvantaged', 'underrepresented'],
                'research': ['research', 'thesis', 'dissertation'],
                'leadership': ['leadership', 'community service', 'volunteer'],
                'sports': ['sports', 'athletic', 'football', 'basketball']
            }
            
            # Check all keyword categories
            all_categories = [level_keywords, field_keywords, gender_keywords, 
                            location_keywords, special_keywords]
            
            for category in all_categories:
                for tag, keywords in category.items():
                    if any(keyword in all_text for keyword in keywords):
                        tags.add(tag)
            
            # Look for explicit tags in HTML
            try:
                # Check meta keywords
                meta_keywords = self.driver.find_element(By.CSS_SELECTOR, 'meta[name="keywords"]')
                keywords_content = meta_keywords.get_attribute('content')
                if keywords_content:
                    meta_tags = [tag.strip().lower() for tag in keywords_content.split(',')]
                    tags.update(meta_tags[:5])  # Limit to 5 meta tags
            except:
                pass
            
            # Check for category/tag elements
            try:
                tag_selectors = [
                    '.tags a', '.categories a', '.tag', '.category',
                    '[class*="tag"]', '[class*="category"]'
                ]
                
                for selector in tag_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements[:5]:  # Limit to 5 elements
                            tag_text = element.text.strip().lower()
                            if tag_text and len(tag_text) < 50:
                                tags.add(tag_text)
                    except:
                        continue
            except:
                pass
            
            # Convert to list and limit to reasonable number
            final_tags = list(tags)[:10]  # Limit to 10 tags
            
            # Clean up tags
            cleaned_tags = []
            for tag in final_tags:
                tag = re.sub(r'[^\w\s-]', '', tag)  # Remove special characters
                tag = re.sub(r'\s+', ' ', tag).strip()  # Clean whitespace
                if len(tag) > 1 and len(tag) < 30:  # Reasonable length
                    cleaned_tags.append(tag)
            
            return cleaned_tags if cleaned_tags else ['general']
            
        except Exception as e:
            print(f"Error extracting tags: {str(e)}")
            return ['general']

    def parse_date_string(self, date_str):
        """Parse date string to datetime object"""
        date_str = date_str.strip()
        
        # Remove common prefixes/suffixes
        date_str = re.sub(r'^(on|by|from|until|before|after)\s+', '', date_str, flags=re.IGNORECASE)
        date_str = re.sub(r'\s+(onwards?|forward)$', '', date_str, flags=re.IGNORECASE)
        
        # Common date formats
        date_formats = [
            '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d',
            '%d-%m-%Y', '%B %d, %Y', '%d %B %Y',
            '%b %d, %Y', '%d %b %Y', '%Y/%m/%d',
            '%d.%m.%Y', '%Y.%m.%d'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        
        return None

    def extract_tags(self):
        """Extract tags/categories for the scholarship"""
        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            title_text = self.driver.title.lower()
            
            # Combine all text for analysis
            all_text = f"{page_text} {title_text}"
            
            tags = set()
            
            # Only include sensible/relevant tags
            sensible_keywords = {
                'undergraduate': ['undergraduate', 'bachelor', 'bsc', 'ba', 'first degree'],
                'postgraduate': ['postgraduate', 'masters', 'msc', 'ma', 'phd', 'doctorate'],
                'highschool': ['secondary', 'high school', 'ssce', 'waec', 'neco'],
                'international': ['international', 'global', 'worldwide', 'abroad'],
                'merit': ['merit', 'academic excellence', 'outstanding'],
                'need': ['need', 'financial aid', 'low income', 'need-based']
            }
            
            # Check for sensible keywords only
            for tag, keywords in sensible_keywords.items():
                if any(keyword in all_text for keyword in keywords):
                    tags.add(tag)
            
            # Look for explicit tags in HTML (but filter them)
            try:
                # Check meta keywords
                meta_keywords = self.driver.find_element(By.CSS_SELECTOR, 'meta[name="keywords"]')
                keywords_content = meta_keywords.get_attribute('content')
                if keywords_content:
                    meta_tags = [tag.strip().lower() for tag in keywords_content.split(',')]
                    # Only add meta tags that match our sensible keywords
                    for meta_tag in meta_tags[:5]:
                        if meta_tag in sensible_keywords.keys():
                            tags.add(meta_tag)
            except:
                pass
            
            # Check for category/tag elements (but filter them)
            try:
                tag_selectors = [
                    '.tags a', '.categories a', '.tag', '.category',
                    '[class*="tag"]', '[class*="category"]'
                ]
                
                for selector in tag_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements[:5]:  # Limit to 5 elements
                            tag_text = element.text.strip().lower()
                            # Only add if it matches our sensible keywords
                            if tag_text in sensible_keywords.keys():
                                tags.add(tag_text)
                    except:
                        continue
            except:
                pass
            
            # Convert to list and ensure we have the sensible tags only
            final_tags = [tag for tag in tags if tag in sensible_keywords.keys()]
            
            return final_tags if final_tags else ['general']
            
        except Exception as e:
            print(f"Error extracting tags: {str(e)}")
            return ['general']
        

class ScholarshipListScraper:
    def __init__(self):
        self.driver = None
        self.base_url = None
        
    def connect_browser(self):
        """Connect to local Chrome browser"""
        print('Starting local Chrome browser...')
        
        # Chrome options for anti-detection
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Optional: Add headless mode
        options.add_argument('--headless')
        
        # Optional: Specify ChromeDriver path if not in PATH
        # service = Service('/path/to/chromedriver')
        # self.driver = webdriver.Chrome(service=service, options=options)
        
        # Use ChromeDriver from PATH
        self.driver = webdriver.Chrome(options=options)
        
        # Anti-detection script
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print('Local Chrome browser started!')
    
    def scrape_scholarship_list(self, list_url, max_scholarships=None):
        """
        Scrape a page containing multiple scholarship links
        Returns list of scholarship URLs with basic info
        """
        try:
            self.connect_browser()
            self.base_url = f"{urlparse(list_url).scheme}://{urlparse(list_url).netloc}"
            
            print(f'Navigating to scholarship list: {list_url}')
            self.driver.get(list_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Take screenshot for debugging
            # print('Taking screenshot of list page...')
            # self.driver.get_screenshot_as_file('./scholarship_list_page.png')
            
            # Handle pagination if needed
            all_scholarship_links = []
            page_num = 1
            
            while True:
                print(f'Extracting scholarships from page {page_num}...')
                
                # Extract scholarship links from current page
                page_links = self.extract_scholarship_links_from_page()
                
                if not page_links:
                    print("No more scholarship links found.")
                    break
                
                all_scholarship_links.extend(page_links)
                print(f'Found {len(page_links)} scholarships on page {page_num}')
                
                # Check if we've reached the maximum
                if max_scholarships and len(all_scholarship_links) >= max_scholarships:
                    all_scholarship_links = all_scholarship_links[:max_scholarships]
                    print(f'Reached maximum of {max_scholarships} scholarships')
                    break
                
                # Try to go to next page
                if not self.go_to_next_page():
                    print("No more pages available.")
                    break
                
                page_num += 1
                time.sleep(2)  # Be respectful with requests
            
            print(f'Total scholarships found: {len(all_scholarship_links)}')
            return all_scholarship_links
            
        except Exception as e:
            print(f"Error scraping scholarship list: {str(e)}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
                print('Browser connection closed.')
    
    def extract_scholarship_links_from_page(self):
        """Extract scholarship links from the current page"""
        scholarship_links = []
        
        # Common selectors for scholarship links
        link_selectors = [
            # Generic article/post links
            "article a[href]",
            ".post a[href]",
            ".entry a[href]",
            
            # Scholarship-specific selectors
            "a[href*='scholarship']",
            "a[href*='grant']",
            "a[href*='award']",
            "a[href*='fellowship']",
            
            # Title-based selectors
            "h1 a, h2 a, h3 a, h4 a",
            ".title a",
            ".post-title a",
            ".entry-title a",
            
            # List-based selectors
            "ul li a[href]",
            "ol li a[href]",
            
            # Card/box-based layouts
            ".card a[href]",
            ".box a[href]",
            ".item a[href]",
            
            # WordPress/blog specific
            ".wp-block-post-title a",
            ".post-link a",
            
            # Table-based layouts
            "table td a[href]",
            "tbody tr a[href]"
        ]
        
        processed_urls = set()
        
        for selector in link_selectors:
            try:
                links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                for link in links:
                    try:
                        href = link.get_attribute('href')
                        text = link.text.strip()
                        
                        if not href or not text:
                            continue
                        
                        # Convert relative URLs to absolute
                        full_url = urljoin(self.base_url, href)
                        
                        # Skip if already processed
                        if full_url in processed_urls:
                            continue
                        
                        # Filter out non-scholarship links
                        if self.is_scholarship_link(href, text):
                            scholarship_info = {
                                'title': text,
                                'url': full_url,
                                'extracted_from': selector
                            }
                            
                            # Try to get additional info from parent elements
                            additional_info = self.extract_additional_info(link)
                            scholarship_info.update(additional_info)
                            
                            scholarship_links.append(scholarship_info)
                            processed_urls.add(full_url)
                            
                    except Exception as e:
                        continue
                        
            except Exception as e:
                continue
        
        # Remove duplicates and sort by relevance
        unique_scholarships = []
        seen_titles = set()
        
        for scholarship in scholarship_links:
            title_clean = re.sub(r'[^\w\s]', '', scholarship['title'].lower())
            if title_clean not in seen_titles and len(title_clean) > 10:
                unique_scholarships.append(scholarship)
                seen_titles.add(title_clean)
        
        return unique_scholarships
    
    def is_scholarship_link(self, href, text):
        """Determine if a link is likely a scholarship link"""
        # URL-based filtering
        url_keywords = ['scholarship', 'grant', 'award', 'fellowship', 'bursary', 'funding']
        url_lower = href.lower()
        
        # Text-based filtering
        text_keywords = ['scholarship', 'grant', 'award', 'fellowship', 'bursary', 'funding', 'opportunity']
        text_lower = text.lower()
        
        # Exclude unwanted links
        exclude_keywords = [
            'contact', 'about', 'home', 'login', 'register', 'privacy', 
            'terms', 'cookie', 'sitemap', 'rss', 'feed', 'category',
            'tag', 'author', 'archive', 'search', 'facebook', 'twitter',
            'instagram', 'linkedin', 'youtube', 'whatsapp', 'telegram'
        ]
        
        # Check if URL or text contains scholarship keywords
        has_scholarship_keyword = (
            any(keyword in url_lower for keyword in url_keywords) or
            any(keyword in text_lower for keyword in text_keywords)
        )
        
        # Check if it's not an excluded link
        not_excluded = not any(keyword in url_lower or keyword in text_lower for keyword in exclude_keywords)
        
        # Additional filters
        is_valid_length = len(text) > 10 and len(text) < 200
        is_not_just_numbers = not text.isdigit()
        
        return has_scholarship_keyword and not_excluded and is_valid_length and is_not_just_numbers
    
    def extract_additional_info(self, link_element):
        """Extract additional information around the link"""
        additional_info = {}
        
        try:
            # Try to find deadline information
            parent = link_element.find_element(By.XPATH, "./..")
            parent_text = parent.text
            
            # Look for dates
            date_patterns = [
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b',
                r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',
                r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b',
                r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b',
                r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'
            ]
            
            for pattern in date_patterns:
                dates = re.findall(pattern, parent_text, re.IGNORECASE)
                if dates:
                    additional_info['potential_deadline'] = dates[0]
                    break
            
            # Look for monetary amounts
            money_pattern = r'[\$₦£€¥]\s*[\d,]+(?:\.\d{2})?'
            amounts = re.findall(money_pattern, parent_text)
            if amounts:
                additional_info['potential_amount'] = amounts[0]
            
            # Look for country/location info
            countries = ['Nigeria', 'USA', 'UK', 'Canada', 'Australia', 'Germany', 'France']
            for country in countries:
                if country.lower() in parent_text.lower():
                    additional_info['potential_location'] = country
                    break
                    
        except Exception as e:
            pass
        
        return additional_info
    
    def go_to_next_page(self):
        """Try to navigate to the next page"""
        next_selectors = [
            "a[href*='page'][href*='2']",
            ".next-page a",
            ".pagination .next a",
            "a:contains('Next')",
            "a:contains('>')",
            ".wp-pagenavi .next a",
            ".page-numbers.next"
        ]
        
        for selector in next_selectors:
            try:
                if ':contains(' in selector:
                    # Use XPath for text-based selection
                    text = selector.split(':contains(')[1].split(')')[0].strip("'\"")
                    xpath = f"//a[contains(text(), '{text}')]"
                    next_links = self.driver.find_elements(By.XPATH, xpath)
                else:
                    next_links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                if next_links:
                    next_link = next_links[0]
                    if next_link.is_enabled():
                        self.driver.execute_script("arguments[0].click();", next_link)
                        time.sleep(3)  # Wait for page to load
                        return True
                        
            except Exception as e:
                continue
        
        return False
    

class ScholarshipBatchProcessor:
    def __init__(self):
        """
        Initialize with your detailed scholarship scraper function
        detail_scraper_func should take a URL and return scholarship details
        """
        
        self.scraper = ScholarshipSeleniumScraper()
        # self.detail_scraper = scraper.scrape_scholarship_data()
        self.list_scraper = ScholarshipListScraper()
        
    def process_scholarship_list(self, list_url, max_scholarships=None, delay_between_scrapes=3):
        """
        Complete pipeline: Get list of scholarships, then scrape each one for details
        Returns nested dictionary structure with batch metadata and scholarship data
        """
        print(f"Starting batch processing for: {list_url}")
        print("="*60)
        
        # Step 1: Get list of scholarship URLs
        print("STEP 1: Extracting scholarship URLs from list page...")
        scholarship_links = self.list_scraper.scrape_scholarship_list(list_url, max_scholarships)
        
        if not scholarship_links:
            print("No scholarship links found!")
            return self._create_empty_batch_result(list_url)
        
        print(f"Found {len(scholarship_links)} scholarship links to process")
        
        # Step 2: Process each scholarship for detailed information
        print("\nSTEP 2: Scraping detailed information for each scholarship...")
        detailed_scholarships = []
        successful_scrapes = 0
        failed_scrapes = 0
        
        for i, scholarship in enumerate(scholarship_links, 1):
            print(f"\nProcessing {i}/{len(scholarship_links)}: {scholarship['title'][:50]}...")
            
            try:
                # Use your detailed scraper
                detailed_data = self.scraper.scrape_scholarship_data((scholarship['url']))
                
                if detailed_data and isinstance(detailed_data, dict):
                    # Use scholarship title/name as the key
                    scholarship_name = detailed_data.get('title', scholarship['title'])
                    if not scholarship_name:
                        scholarship_name = f"Scholarship_{i}"
                    
                    # Create nested structure for each scholarship
                    scholarship_entry = {
                        'name': scholarship_name,
                        'source_info': {
                            'list_title': scholarship['title'],
                            'source_url': scholarship['url'],
                            'scraped_at': datetime.now().isoformat()
                        },
                        'scholarship_data': detailed_data,
                        'additional_list_info': {k: v for k, v in scholarship.items() 
                                               if k not in ['title', 'url']}
                    }
                    detailed_scholarships.append(scholarship_entry)
                    successful_scrapes += 1
                    print(f"✓ Successfully scraped details")
                else:
                    failed_scrapes += 1
                    print(f"✗ Failed to scrape details - no data returned")
                
            except Exception as e:
                failed_scrapes += 1
                print(f"✗ Error scraping {scholarship['url']}: {str(e)}")
            
            # Respectful delay between requests
            if i < len(scholarship_links):
                print(f"Waiting {delay_between_scrapes} seconds before next request...")
                time.sleep(delay_between_scrapes)
        
        # Step 3: Create nested batch result structure
        batch_result = self._create_batch_result(
            list_url, 
            detailed_scholarships, 
            len(scholarship_links),
            successful_scrapes,
            failed_scrapes
        )
        
        # Step 4: Save comprehensive results (removed - just return the data)
        
        print(f"\nBatch processing completed!")
        print(f"Successfully scraped {successful_scrapes} out of {len(scholarship_links)} scholarships")
        print(f"Failed scrapes: {failed_scrapes}")
        
        return batch_result
    
    def _create_batch_result(self, source_url, scholarships, total_found, successful, failed):
        """Create nested dictionary structure for batch results"""
        return {
            'batch_metadata': {
                'batch_id': f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'source_url': source_url,
                'processed_at': datetime.now().isoformat(),
                'scraper_version': '2.0',
                'processing_stats': {
                    'total_scholarships_found': total_found,
                    'successful_scrapes': successful,
                    'failed_scrapes': failed,
                    'success_rate': f"{(successful/total_found*100):.1f}%" if total_found > 0 else "0%"
                }
            },
            'scholarships': {
                scholarship['name']: scholarship 
                for scholarship in scholarships
            },
            'summary': {
                'total_scholarships': len(scholarships),
                'scholarship_names': [scholarship['name'] for scholarship in scholarships],
                'available_fields': self._get_available_fields(scholarships) if scholarships else []
            }
        }
    
    def _create_empty_batch_result(self, source_url):
        """Create empty batch result structure when no scholarships found"""
        return {
            'batch_metadata': {
                'batch_id': f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'source_url': source_url,
                'processed_at': datetime.now().isoformat(),
                'scraper_version': '2.0',
                'processing_stats': {
                    'total_scholarships_found': 0,
                    'successful_scrapes': 0,
                    'failed_scrapes': 0,
                    'success_rate': "0%"
                }
            },
            'scholarships': {},
            'summary': {
                'total_scholarships': 0,
                'scholarship_names': [],
                'available_fields': []
            }
        }
    
    def _get_available_fields(self, scholarships):
        """Extract available fields from scraped scholarships"""
        if not scholarships:
            return []
        
        all_fields = set()
        for scholarship in scholarships:
            if 'scholarship_data' in scholarship and isinstance(scholarship['scholarship_data'], dict):
                all_fields.update(scholarship['scholarship_data'].keys())
        
        return sorted(list(all_fields))




def main_scholarship_scraper(list_url, max_scholarships=None, delay_between_scrapes=3):
    """
    Complete scholarship scraping pipeline that combines all three classes:
    1. ScholarshipListScraper - extracts scholarship URLs from list pages
    2. ScholarshipScraper - scrapes detailed info from individual scholarship pages  
    3. ScholarshipBatchProcessor - orchestrates the entire process
    
    Args:
        list_url (str): URL of the page containing scholarship listings
        max_scholarships (int, optional): Maximum number of scholarships to process
        delay_between_scrapes (int): Seconds to wait between individual scholarship scrapes
        save_to_file (bool): Whether to save results to a JSON file
    
    Returns:
        dict: Nested dictionary with batch metadata and scholarship data
    """
    try:
        # Initialize the batch processor with the detailed scraper
        batch_processor = ScholarshipBatchProcessor()
        
        # Start the complete pipeline
        start_time = datetime.now()
        
        # Process the scholarship list
        results = batch_processor.process_scholarship_list(
            list_url=list_url,
            max_scholarships=max_scholarships,
            delay_between_scrapes=delay_between_scrapes
        )
        
        end_time = datetime.now()
        processing_time = end_time - start_time
        
        return results
        
    except Exception as e:
        return None
