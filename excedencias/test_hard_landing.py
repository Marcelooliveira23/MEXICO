import pandas as pd
import os

# Testar todos os arquivos CSV
arquivos = [
    r'c:\Users\mrced\OneDrive\Documents\hard landing\CRC212 20-2-25 Hard landing 1.csv',
    r'c:\Users\mrced\OneDrive\Documents\hard landing\XA-ALU _HL_13AGO25_FLT651.CSV',
    r'c:\Users\mrced\OneDrive\Documents\hard landing\HL XA-ALL AM593 20251026.csv',
    r'c:\Users\mrced\OneDrive\Documents\hard landing\CRC212 20-2-25 Hard landing 2.csv',
]

print("=" * 80)
print("TESTE DE DETECÇÃO DE HARD LANDING - E190")
print("Threshold: 2.6G (Hard Landing) | 2.8G (Very Hard Landing)")
print("=" * 80)

for arquivo in arquivos:
    if not os.path.exists(arquivo):
        print(f"\n❌ Arquivo não encontrado: {arquivo}")
        continue
    
    nome = os.path.basename(arquivo)
    print(f"\n\n{'='*80}")
    print(f"📁 {nome}")
    print(f"{'='*80}")
    
    try:
        # Ler CSV
        df = pd.read_csv(arquivo, low_memory=False)
        print(f"✅ Carregado: {len(df)} linhas")
        
        # Mostrar colunas
        print(f"\nColunas disponíveis:")
        for col in df.columns:
            print(f"  - {col}")
        
        # Verificar se tem coluna Vertical Acceleration
        accel_col = None
        for col in df.columns:
            if 'vertical' in col.lower() and 'accel' in col.lower():
                accel_col = col
                break
            elif 'normaccel' in col.lower():
                accel_col = col
                break
            elif 'normal load' in col.lower():
                accel_col = col
                break
        
        if not accel_col:
            print("❌ Coluna de aceleração vertical não encontrada!")
            continue
        
        print(f"\n📊 Usando coluna: '{accel_col}'")
        
        # Converter para numérico
        df[accel_col] = pd.to_numeric(df[accel_col], errors='coerce')
        df_clean = df[df[accel_col].notna()]
        
        # Estatísticas
        min_g = df_clean[accel_col].min()
        max_g = df_clean[accel_col].max()
        mean_g = df_clean[accel_col].mean()
        
        print(f"\n📈 Estatísticas:")
        print(f"  Min: {min_g:.3f}G")
        print(f"  Max: {max_g:.3f}G")
        print(f"  Média: {mean_g:.3f}G")
        
        # Detectar hard landing
        hard_landing = df_clean[df_clean[accel_col] > 2.6]
        very_hard = df_clean[df_clean[accel_col] > 2.8]
        
        print(f"\n🔍 DETECÇÃO:")
        print(f"  Hard Landing (> 2.6G): {len(hard_landing)} eventos")
        print(f"  Very Hard Landing (> 2.8G): {len(very_hard)} eventos")
        
        if len(hard_landing) > 0:
            print(f"\n⚠️ HARD LANDING DETECTADO!")
            print(f"\nPicos encontrados:")
            for idx in hard_landing.head(10).index:
                g_force = df_clean.loc[idx, accel_col]
                time_col = [c for c in df.columns if 'time' in c.lower() or 'date' in c.lower()]
                if time_col:
                    timestamp = df_clean.loc[idx, time_col[0]]
                    print(f"  • {timestamp}: {g_force:.3f}G")
                else:
                    print(f"  • Linha {idx}: {g_force:.3f}G")
        else:
            print(f"\n✅ Nenhum hard landing detectado (max < 2.6G)")
            
    except Exception as e:
        print(f"❌ Erro ao processar: {e}")

print(f"\n\n{'='*80}")
print("FIM DO TESTE")
print(f"{'='*80}")
