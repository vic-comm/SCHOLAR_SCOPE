/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "../templates/**/*.html", 
     "../**/templates/**/*.html",   // your Django templates
    "../static/js/**/*.js",
    "../**/forms.py"      // any JS files using Tailwind classes
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
