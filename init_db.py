from app import create_app, db

def init_database():
    print("Inicializando banco de dados...")
    app = create_app()
    with app.app_context():
        db.create_all()
        print("Tabelas criadas com sucesso!")

if __name__ == "__main__":
    init_database() 