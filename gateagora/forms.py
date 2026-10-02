# -*- coding: utf-8 -*-
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Empresa, Perfil


class NovoUsuarioForm(forms.Form):
    first_name = forms.CharField(label="Nome", max_length=150)
    last_name  = forms.CharField(label="Sobrenome", max_length=150, required=False)
    email      = forms.EmailField(label="E-mail")
    username   = forms.CharField(label="Usuário", max_length=150)
    telefone   = forms.CharField(label="WhatsApp (com DDD)", max_length=20, required=False)
    cargo      = forms.ChoiceField(label="Cargo", choices=Perfil.Cargo.choices)
    empresa    = forms.ModelChoiceField(
        label="Empresa", queryset=Empresa.objects.none(), required=False
    )
    password1  = forms.CharField(label="Senha", widget=forms.PasswordInput)
    password2  = forms.CharField(label="Confirmar senha", widget=forms.PasswordInput)

    def __init__(self, *args, request_user=None, empresa_atual=None, **kwargs):
        super().__init__(*args, **kwargs)
        if request_user is not None and request_user.is_superuser:
            # só superuser escolhe a empresa; Gestor sempre usa a própria
            self.fields['empresa'].queryset = Empresa.objects.all()
            self.fields['empresa'].required = True
            self.fields['empresa'].initial = empresa_atual
        else:
            del self.fields['empresa']

    def clean_username(self):
        u = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=u).exists():
            raise ValidationError("Este usuário já existe.")
        return u

    def clean_email(self):
        e = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=e).exists():
            raise ValidationError("Este e-mail já está cadastrado.")
        return e

    def clean(self):
        cd = super().clean()
        p1, p2 = cd.get('password1'), cd.get('password2')
        # Senha livre: sem validate_password. Só exige que as duas conferam.
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "As senhas não conferem.")
        return cd
