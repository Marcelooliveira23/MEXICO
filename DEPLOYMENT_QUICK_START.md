# 🚀 AI 9.0 - DEPLOYMENT RÁPIDO (5 MINUTOS)

## ⚡ START HERE

### 1️⃣ COPIAR MÓDULOS
```powershell
# No PowerShell, execute:
Copy-Item "c:\Troubleshooting\ai_9_0_semantic_core.py" -Destination "c:\Troubleshooting\"
Copy-Item "c:\Troubleshooting\ai_9_0_lru_specialist.py" -Destination "c:\Troubleshooting\"
Copy-Item "c:\Troubleshooting\ai_9_0_e2_fleet.py" -Destination "c:\Troubleshooting\"
Copy-Item "c:\Troubleshooting\routes_ai_9_0.py" -Destination "c:\Troubleshooting\"
Copy-Item "c:\Troubleshooting\e2_fleet_dashboard_ai_9_0.html" -Destination "c:\Troubleshooting\Templates\"

# Verificar cópia
dir c:\Troubleshooting\ai_9_0_*.py
dir c:\Troubleshooting\routes_ai_9_0.py
dir c:\Troubleshooting\Templates\e2_fleet_dashboard_ai_9_0.html
```

### 2️⃣ REGISTRAR BLUEPRINT NO APP
Editar `c:\Troubleshooting\app.py`:

```python
# Adicione APÓS as outras importações de blueprints:
from routes_ai_9_0 import ai_9_0_blueprint

# E ANTES de app.run():
app.register_blueprint(ai_9_0_blueprint)
```

### 3️⃣ TESTAR ENDPOINTS
```powershell
# Terminal novo, execute:
$headers = @{"Content-Type" = "application/json"}

# Teste 1: Semantic Core - Disambiguate
$body1 = @{
    query = "LRU removal em MXB"
    context = "maintenance"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:5000/api/ai/v2/disambiguation" `
    -Method POST `
    -Headers $headers `
    -Body $body1 | ConvertTo-Json -Depth 10

# Teste 2: Fleet Snapshot
Invoke-RestMethod -Uri "http://localhost:5000/api/ai/v2/e2/fleet-snapshot" `
    -Method GET | ConvertTo-Json -Depth 10

# Teste 3: LRU Identification
$body3 = @{
    query = "MXB hydraulic pump removal"
    tail = "MXB"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:5000/api/ai/v2/lru-identification" `
    -Method POST `
    -Headers $headers `
    -Body $body3 | ConvertTo-Json -Depth 10
```

### 4️⃣ VISITE LANDING PAGE
```
Abra o navegador:
http://localhost:5000/fleet/e2
```

Você deve ver:
- ✅ Status da frota E2
- ✅ Widget Copilot v2
- ✅ Links para endpoints inteligentes

### 5️⃣ TESTE COPILOT V2
```
Na landing page, digite:
"LRU removal em MXB"

Você deve receber:
✅ ATA 29 (não 45)
✅ Procedures de remoção 
✅ Dados MTBF
✅ Similar cases na frota
✅ Reasoning trace visível
```

---

## ✅ CHECKLIST MÍNIMO

- [ ] Módulos copiados (5 arquivos)
- [ ] Blueprint registrado em app.py
- [ ] Flask restarted
- [ ] POST /api/ai/v2/disambiguation funciona
- [ ] GET /api/ai/v2/e2/fleet-snapshot retorna JSON
- [ ] Landing page /fleet/e2 carrega
- [ ] Query "LRU removal em MXB" → ATA 29 (correto!)
- [ ] Copilot v2 responde inteligentemente

---

## 🔧 TROUBLESHOOTING

### ❌ ModuleNotFoundError: routes_ai_9_0
**Solução**: Verifique se `routes_ai_9_0.py` está em `c:\Troubleshooting\`

```python
# app.py must include:
import sys
sys.path.insert(0, os.path.dirname(__file__))
from routes_ai_9_0 import ai_9_0_blueprint
```

### ❌ 404 on /api/ai/v2//*
**Solução**: Blueprint não foi registrado. Adicione:
```python
app.register_blueprint(ai_9_0_blueprint)
```

### ❌ Empty response from /fleet/e2
**Solução**: ensure `e2_fleet_dashboard_ai_9_0.html` está em `Templates/`

### ❌ Copilot v2 não responde
**Solução**: Endpoints devem estar rodando. Teste:
```bash
curl http://localhost:5000/api/ai/v2/e2/fleet-snapshot
```

### ❌ Timeout em endpoints
**Solução**: Endpoints de "fleet-snapshot" podem ser lentos. Aumente timeout para 10s.

---

## 📊 VALIDAÇÃO DE SUCESSO

Execute este script para validar tudo:

```python
# save as: validate_ai_9_0.py
import requests
import json

BASE_URL = "http://localhost:5000"

tests = {
    "Fleet Snapshot": {
        "method": "GET",
        "endpoint": "/api/ai/v2/e2/fleet-snapshot",
        "expected": ["fleet_status", "health", "components"]
    },
    "Disambiguation": {
        "method": "POST",
        "endpoint": "/api/ai/v2/disambiguation",
        "body": {"query": "LRU removal em MXB", "context": "maintenance"},
        "expected": ["intent", "confidence", "atas"]
    },
    "LRU Identification": {
        "method": "POST",
        "endpoint": "/api/ai/v2/lru-identification",
        "body": {"query": "MXB hydraulic pump removal", "tail": "MXB"},
        "expected": ["component", "ata", "procedures"]
    },
    "MEL Compliance": {
        "method": "GET",
        "endpoint": "/api/ai/v2/e2/mel-compliance",
        "expected": ["mel_items", "compliance_status"]
    }
}

print("🧪 Validating AI 9.0 Deployment...\n")
passed = 0
failed = 0

for test_name, test_config in tests.items():
    try:
        if test_config["method"] == "GET":
            resp = requests.get(f"{BASE_URL}{test_config['endpoint']}", timeout=10)
        else:
            resp = requests.post(
                f"{BASE_URL}{test_config['endpoint']}", 
                json=test_config.get("body", {}),
                timeout=10
            )
        
        if resp.status_code == 200:
            data = resp.json()
            expected_keys = test_config.get("expected", [])
            if all(key in str(data) for key in expected_keys):
                print(f"✅ {test_name}: PASS")
                passed += 1
            else:
                print(f"⚠️  {test_name}: Incomplete response")
                failed += 1
        else:
            print(f"❌ {test_name}: HTTP {resp.status_code}")
            failed += 1
    except Exception as e:
        print(f"❌ {test_name}: {str(e)}")
        failed += 1

print(f"\n📊 Results: {passed} passed, {failed} failed")
if failed == 0:
    print("🎉 AI 9.0 is ready for production!")
```

Execute:
```bash
python validate_ai_9_0.py
```

---

## 🎯 PRÓXIMOS PASSOS (AFTER DEPLOYMENT)

1. **Gather User Feedback** (24 horas)
   - Como users interagem com Copilot v2?
   - Alguma query gera resposta errada?
   - Performance é aceitável?

2. **Performance Tuning** (Semana 1)
   - Profile endpoints mais lentos
   - Adicionar caching em endpoints pesados
   - Index database tables

3. **Phase 6-10 Features** (Semanas 2-4)
   - Implementar as 62+ melhorias mapeadas
   - Voice interface
   - Mobile app
   - ERP integration

---

## 📞 EMERGENCY CONTACTS

Se algo quebrar severamente:

1. **Rollback** (voltar ao AI 8.0):
   ```python
   # Em app.py, comente:
   # app.register_blueprint(ai_9_0_blueprint)
   
   # Restart Flask
   ```

2. **Check Logs**:
   ```bash
   tail -100 flask_server.log
   ```

3. **Database validation**:
   ```python
   # verify_db.py
   import sqlite3
   conn = sqlite3.connect('app.db')
   cursor = conn.cursor()
   cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
   print(cursor.fetchall())
   ```

---

**Time to Deploy**: 5 minutes  
**Time to Validate**: 5 minutes  
**Time to Impact**: Immediate  

**Status**: 🚀 READY

---

Created: 25 de Março de 2026  
Version: AI 9.0 Deployment Guide v1
