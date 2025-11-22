from django import forms
from .models import Application, Scholarship, Profile

class ScholarshipModelForm(forms.ModelForm):
    class Meta:
        model = Scholarship
        fields = ['title','start_date','end_date','tags','description','reward','active','link', 'eligibility']

    

class ApplicationStatusUpdateForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['status']
        widgets = {'status': forms.Select(attrs={'class':'form-select', 'onchange':'this.form.submit()'})}

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        exclude = ['created_at', 'updated_at', 'user',]
        widgets = {
            'tags': forms.CheckboxSelectMultiple,   
            'level': forms.CheckboxSelectMultiple,  
        }