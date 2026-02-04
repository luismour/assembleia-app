from passlib.context import CryptContext

# Configura a criptografia
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# A senha que você quer
senha_pura = "saps"

# Gera o Hash
hash_gerado = pwd_context.hash(senha_pura)

print("\n--- COPIE O CÓDIGO ABAIXO ---")
print(hash_gerado)
print("-----------------------------\n")