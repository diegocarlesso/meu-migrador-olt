# OLT Config Migrator (PyQt6) 🚇🛠️

Protótipo funcional para:
- Selecionar fabricante de **origem**, carregar backup (.txt/.cfg)
- Selecionar fabricante de **destino**
- Editar **VLANs / perfis / IPs / rotas** em tabelas (com ADD/Remove)
- Ver **prévia do script** e **gerar arquivo** com extensão padrão do fabricante

> **Aviso**: este é um “esqueleto bem útil”: ele já faz parsing e geração **best-effort** para alguns fabricantes e deixa a arquitetura pronta para você ir plugando regras e seções específicas.

## Como rodar

1) Instale dependência:
```bash
pip install PyQt6
```

2) Execute:
```bash
python main.py
```

## Como adicionar um fabricante novo

Crie um arquivo em `app/vendors/` implementando `VendorAdapter`:
- `parse_to_normalized(text) -> NormalizedConfig`
- `schema() -> list[SectionSchema]`
- `from_normalized(normalized) -> dict[str, list[dict]]`
- `render(target_data) -> str`

Depois registre no `app/vendors/registry.py`.

## Onde ajustar cores/tema

`app/styles.py`
