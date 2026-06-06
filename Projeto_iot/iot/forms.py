from django import forms
from django.contrib.auth.models import User


class CadastroForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={"placeholder": "Digite sua senha"})
    )

    password2 = forms.CharField(
        label="Confirmar senha",
        widget=forms.PasswordInput(attrs={"placeholder": "Confirme sua senha"})
    )

    class Meta:
        model = User
        fields = ["username", "email"]
        labels = {
            "username": "Usuário",
            "email": "E-mail",
        }
        widgets = {
            "username": forms.TextInput(attrs={"placeholder": "Digite seu usuário"}),
            "email": forms.EmailInput(attrs={"placeholder": "Digite seu e-mail"}),
        }

    def clean_password2(self):
        senha1 = self.cleaned_data.get("password1")
        senha2 = self.cleaned_data.get("password2")

        if senha1 and senha2 and senha1 != senha2:
            raise forms.ValidationError("As senhas não são iguais.")

        return senha2

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data["password1"])

        if commit:
            usuario.save()

        return usuario