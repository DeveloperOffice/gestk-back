"""
Script para monitorar o progresso do ETL 06 em tempo real
Consulta o banco de dados a cada 5 segundos e exibe a evolução
"""
import os
import sys
import django
import time
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestk.settings')
django.setup()

from apps.contabil.models import LancamentoContabil, Partida
from apps.core.models import Contabilidade

def limpar_tela():
    """Limpa a tela do terminal"""
    os.system('cls' if os.name == 'nt' else 'clear')

def formatar_numero(numero):
    """Formata número com separador de milhares"""
    return f"{numero:,}".replace(',', '.')

def calcular_velocidade(registros_atuais, registros_anteriores, tempo_decorrido):
    """Calcula a velocidade de importação (registros/segundo)"""
    if tempo_decorrido == 0:
        return 0
    return (registros_atuais - registros_anteriores) / tempo_decorrido

def estimar_tempo_restante(registros_atuais, total_esperado, velocidade):
    """Estima o tempo restante para conclusão"""
    if velocidade == 0:
        return "Calculando..."
    
    registros_restantes = total_esperado - registros_atuais
    segundos_restantes = registros_restantes / velocidade
    
    horas = int(segundos_restantes // 3600)
    minutos = int((segundos_restantes % 3600) // 60)
    segundos = int(segundos_restantes % 60)
    
    if horas > 0:
        return f"{horas}h {minutos}m {segundos}s"
    elif minutos > 0:
        return f"{minutos}m {segundos}s"
    else:
        return f"{segundos}s"

def monitorar_progresso():
    """Monitora o progresso da importação em tempo real"""
    print("🚀 Iniciando monitoramento do ETL 06 - Lançamentos Contábeis")
    print("=" * 80)
    print("Pressione Ctrl+C para sair\n")
    
    TOTAL_ESPERADO = 7_538_155  # Total de registros a importar
    INTERVALO = 5  # Segundos entre cada verificação
    
    registros_anterior = 0
    tempo_inicio = time.time()
    leituras = []
    
    try:
        while True:
            # Consultar banco de dados
            total_lancamentos = LancamentoContabil.objects.count()
            total_partidas = Partida.objects.count()
            tempo_atual = time.time()
            tempo_decorrido_total = tempo_atual - tempo_inicio
            
            # Calcular velocidade
            velocidade = calcular_velocidade(total_lancamentos, registros_anterior, INTERVALO)
            leituras.append(velocidade)
            
            # Calcular velocidade média (últimas 10 leituras)
            velocidade_media = sum(leituras[-10:]) / len(leituras[-10:]) if leituras else 0
            
            # Calcular progresso
            percentual = (total_lancamentos / TOTAL_ESPERADO * 100) if TOTAL_ESPERADO > 0 else 0
            
            # Criar barra de progresso
            barra_tamanho = 50
            barra_preenchida = int(percentual / 2)
            barra = '█' * barra_preenchida + '░' * (barra_tamanho - barra_preenchida)
            
            # Estimar tempo restante
            tempo_restante = estimar_tempo_restante(total_lancamentos, TOTAL_ESPERADO, velocidade_media)
            
            # Limpar tela e exibir status
            limpar_tela()
            
            print("=" * 80)
            print("🔄  MONITORAMENTO ETL 06 - LANÇAMENTOS CONTÁBEIS")
            print("=" * 80)
            print(f"\n📊  PROGRESSO GERAL")
            print(f"    [{barra}] {percentual:5.2f}%")
            print(f"\n📈  ESTATÍSTICAS")
            print(f"    Lançamentos:        {formatar_numero(total_lancamentos):>12} / {formatar_numero(TOTAL_ESPERADO)}")
            print(f"    Partidas (D+C):     {formatar_numero(total_partidas):>12}")
            print(f"    Registros/lote:     {formatar_numero(1000):>12}")
            print(f"\n⚡  VELOCIDADE")
            print(f"    Atual:              {formatar_numero(int(velocidade)):>12} registros/s")
            print(f"    Média:              {formatar_numero(int(velocidade_media)):>12} registros/s")
            print(f"\n⏱️   TEMPO")
            print(f"    Decorrido:          {time.strftime('%H:%M:%S', time.gmtime(tempo_decorrido_total))}")
            print(f"    Estimado restante:  {tempo_restante}")
            print(f"    Última atualização: {datetime.now().strftime('%H:%M:%S')}")
            print("\n" + "=" * 80)
            print("💡  Dica: O ETL está rodando em segundo plano. Este monitor apenas consulta o BD.")
            print("    Pressione Ctrl+C para sair do monitoramento (o ETL continuará rodando)")
            print("=" * 80)
            
            # Verificar se concluiu
            if total_lancamentos >= TOTAL_ESPERADO:
                print("\n✅  IMPORTAÇÃO CONCLUÍDA!")
                break
            
            registros_anterior = total_lancamentos
            time.sleep(INTERVALO)
            
    except KeyboardInterrupt:
        print("\n\n⏸️   Monitoramento interrompido pelo usuário.")
        print(f"📊  Última leitura: {formatar_numero(total_lancamentos)} lançamentos importados")
        print("💡  O ETL continua rodando em segundo plano!")
    except Exception as e:
        print(f"\n❌  Erro: {e}")

if __name__ == '__main__':
    monitorar_progresso()
