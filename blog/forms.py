from django import forms
from crispy_forms.helper import FormHelper
from blog.models import Post, Comment
from crispy_forms.layout import Layout, Submit, Div, Field, HTML, Row, Column
from ckeditor.fields import RichTextField

class PostForm(forms.ModelForm):
    title = forms.CharField(
        max_length=100, 
        label='What\'s your problem',
        )
    
    content  = forms.CharField(
        widget=forms.Textarea, 
        label='', 
        required=False,
        max_length=10000,
        )

    display_name = forms.CharField(
        max_length=100,
        label='Display Name',
        required=False,
    )
    

    class Meta:
        model = Post
        fields = ('title', 'content', 'media_file', 'display_name')


    def __init__(self, *args, **kwargs):
        super(PostForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_method = 'POST'
        
        self.helper.layout = Layout(
            Div(
                Row('title', css_class='form-group col-md-12 mb-0'),
                Row(
                    Field('content', css_class='w-100'), # Full-width content field
                    css_class='form-group col-md-12 mb-0'
                ),
                Row('media_file', css_class='form-group col-md-12 mb-0'),
                Row('display_name', css_class='form-group col-md-12 mb-0'),
                css_class='form-group mb-0'
            ),
            Submit('submit', 'Submit'),
        )

class ReplyForm(PostForm):
    title = forms.CharField(
        max_length=100, 
        label='Response to post'
        ) 


class PostSearchForm(forms.Form):
    query = forms.CharField(label='Search', max_length=100)

    def __init__(self, *args, **kwargs):
        super(PostSearchForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.add_input(Submit('submit', 'Search'))

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['name', 'content', 'media_file']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Write your comment here...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.form_class = 'comment-form'
        self.helper.layout = Layout(
            Div(
                Row(
                    Field('name', css_class='form-control', wrapper_class='col-6'),
                    css_class='row justify-content-center',  # Aligns form fields
                ),
                Row(
                    Field('content', css_class='form-control', wrapper_class='col-12'),
                    css_class='row justify-content-center',
                ),
                Row(
                    Field('media_file', css_class='form-control', wrapper_class='col-12'),
                    css_class='row justify-content-center',
                ),
            ),
            Div(
                Submit('submit', 'Submit', css_class='btn btn-primary'),
                css_class='row justify-content-center mt-2',
            )
        )