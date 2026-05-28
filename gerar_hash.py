"""
Script para gerar o hash da senha do salão.
Execute localmente: python gerar_hash.py
Copie o hash gerado e cole no Supabase (ver instruções abaixo).
"""
import bcrypt

# Coloque aqui a senha que você usa para logar no sistema
SENHA = "FB-MkkiWmF#P6k_"

hash_gerado = bcrypt.hashpw(SENHA.encode(), bcrypt.gensalt()).decode()
print(f"\nHash gerado:\n{hash_gerado}\n")
print("Cole este hash no Supabase com o SQL abaixo:")
print(f"\nUPDATE agd_empresas SET senha_hash = '{hash_gerado}' WHERE slug = 'studio-bella';\n")
