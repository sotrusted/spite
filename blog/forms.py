from django import forms
from crispy_forms.helper import FormHelper
from .models import Post
from crispy_forms.layout import Layout, Submit, Div, Field, HTML, Row, Column

class PostForm(forms.ModelForm):
    title = forms.CharField(
        max_length=100, 
        label='What\'s your problem'
        )
    
    city = forms.CharField(
        max_length=100, 
        label='city',
        required=False
        )
    
    description = forms.CharField(
        widget=forms.Textarea, 
        label=''
        )
#    images = MultipleImageField(
 #       label='pics', 
  #      required=False
   # )

    image = forms.ImageField(required=False, label='')

    contact = forms.CharField(
        max_length=50, 
        label='contact info', 
        required=False
        )
    

    class Meta:
        model = Post
        fields = ('title', 'city', 'description', 'image', \
                  'contact')


    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'POST'
        
        self.helper.layout = Layout(
            Div(
                Row(
                    Column('title', css_class='form-group col-md-6 mb-0'),
                    Column('city', css_class='form-group col-md-3 mb-0'),
                    css_class='form-row'
                ),
                Row('description', css_class='form-group col-md-9 mb-0'),
                Row('image', css_class='form-group col-md-9 mb-0'),
                Row('contact', css_class='form-group col-md-9 mb-0'
                ),
                css_class='form-group mb-0'
            ),
            Submit('submit', 'Submit'),
        )