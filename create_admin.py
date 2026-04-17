import bcrypt
from app.core.config import settings

def create_password_hash(password: str) -> str:
    """
    Генерирует bcrypt-хеш пароля
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def main():
    print("=== CREATE / UPDATE ADMIN PASSWORD ===")

    password = input("Enter new admin password: ").strip()

    if len(password) < 4:
        print("❌ Password too short (min 4 chars)")
        return

    hashed = create_password_hash(password)

    print("\n✅ Password hash generated:\n")
    print(hashed)

    print("\n👉 Now paste this into your .env file:")
    print(f'ADMIN_PASSWORD_HASH="{hashed}"')


if __name__ == "__main__":
    main()