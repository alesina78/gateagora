# -*- coding: utf-8 -*-
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Autenticação
    path('login/',  views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Aulas
    path('concluir-aula/<int:aula_id>/', views.concluir_aula, name='concluir_aula'),

    # PDFs e relatórios
    path('gerar-relatorio/<int:aluno_id>/', views.gerar_relatorio_pdf,  name='gerar_relatorio_pdf'),
    path('guia-trato/',                     views.gerar_ficha_trato_pdf, name='gerar_ficha_trato_pdf'),

    # Encilhamento
    path('encilhamento/',          views.encilhamento,          name='encilhamento'),
    path('encilhamento/pdf/',      views.encilhamento_pdf,      name='encilhamento_pdf'),
    path('encilhamento/whatsapp/', views.encilhamento_whatsapp, name='encilhamento_whatsapp'),

    # Manejo sanitário
    path('manejo-massa/', views.manejo_em_massa, name='manejo_em_massa'),
]
