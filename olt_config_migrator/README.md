# OLT Config Migrator (Turbo) — PyQt6

Versão focada em migração **Fiberhome → ZTE** com:
- VLANs (incluindo ranges)
- Trunks automáticas (passa todas VLANs nas interfaces escolhidas)
- ONUs completas (cadastro + serviços + PPPoE quando existir)
- Numeração **sempre por ONU** (service-port / wan-ip / gemport)

Também inclui vendors adicionais no menu (Parks, V-Solution, Datacom, Huawei) em modo best-effort.

## Rodar
```bash
pip install PyQt6
python main.py
```

## Dicas rápidas
- Se você não preencher Frame/Slot no “Modo rápido”, o script ZTE sai com placeholders:
  `gpon_olt-[FRAME]/[SLOT]/[PON]`
- Trunks: informe separado por vírgula, ex:
  `xgei-1/1/1, gei-1/1/5`
