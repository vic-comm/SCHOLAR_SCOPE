from django import forms
from .models import Application, Scholarship

class ScholarshipModelForm(forms.ModelForm):
    class Meta:
        model = Scholarship
        fields = ['title','start_date','end_date','tags','description','reward','active','link', 'eligibility']

    

class ApplicationStatusUpdateForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['status']
        widgets = {'status': forms.Select(attrs={'class':'form-select', 'onchange':'this.form.submit()'})}
