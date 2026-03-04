# -*- coding: utf-8 -*-
"""
Configuração de URLs para o projeto Gate 4.
Este arquivo gerencia as rotas do Dashboard, Admin e Geradores de PDF.
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from gateagora import views
from gateagora.views import CustomLoginView  # Importação da sua View customizada

urlpatterns = [
    # --- Painel Administrativo ---
    # Utiliza o tema Unfold conforme configurado no admin.py
    path('admin/', admin.site.urls),

    # --- Autenticação ---
    # Alterado para usar a CustomLoginView que integra o design Dark e o Logo
    path('login/', CustomLoginView.as_view(), name='login'),
    
    # O LogoutView no Django 5.x/6.x exige método POST por segurança. 
    # O redirecionamento após logout volta para a tela de login.
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # --- Dashboard Principal ---
    # Rota raiz que processa KPIs, Gráficos e Agenda
    path('', views.dashboard, name='dashboard'),

    # --- Ações de Aula ---
    # Permite concluir treinos diretamente pelos cards da agenda no dashboard
    path('concluir-aula/<int:aula_id>/', views.concluir_aula, name='concluir_aula'),

    # --- Relatórios e Faturas (PDFs via ReportLab) ---
    # Gera o PDF individual de cobrança do aluno (usado no card de Pendências)
    path('gerar-relatorio/<int:aluno_id>/', views.gerar_relatorio_pdf, name='gerar_relatorio_pdf'),
    
    # Gera o PDF da Guia de Trato organizada por baia para a equipe de cocheira
    path('guia-trato/', views.gerar_ficha_trato_pdf, name='gerar_ficha_trato_pdf'),

    # --- Manejo Sanitário e Coletivo ---
    # Página para aplicação de vacinas e vermífugos em lote
    path('manejo-em-massa/', views.manejo_em_massa, name='manejo_em_massa'),
]

# --- Configuração de Arquivos Estáticos e Mídia ---
# Essencial para exibir fotos dos cavalos e carregar o Tailwind/CSS em ambiente de desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)