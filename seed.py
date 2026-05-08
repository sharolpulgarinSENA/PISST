# seed.py
# Este script inserta datos demo en Neon para poder probar el sistema
from app.core.database import SessionLocal
from app.models.empresa import Empresa
from app.models.area import Area
from app.models.cargo import Cargo
from app.models.user import User, RoleEnum
from app.core.security import get_password_hash

def seed():
    db = SessionLocal()
    try:
        # Verificar si ya existe la empresa demo (evitar duplicados)
        if db.query(Empresa).filter(Empresa.nit == "900123456-1").first():
            print("Seed ya fue ejecutado anteriormente. Saliendo.")
            return

        print("Creando empresa demo...")
        empresa = Empresa(
            nombre="Empresa Demo SENA SA",
            nit="900123456-1",
            sector="Manufactura"
        )
        db.add(empresa)
        db.flush()  # obtener el id sin hacer commit todavía

        print("Creando áreas...")
        areas = [
            Area(nombre="Producción",     empresa_id=empresa.id),
            Area(nombre="Administración", empresa_id=empresa.id),
            Area(nombre="Bodega",         empresa_id=empresa.id),
        ]
        for area in areas:
            db.add(area)
        db.flush()

        print("Creando cargos...")
        cargos = [
            Cargo(nombre="Operario de Máquina",      area_id=areas[0].id, empresa_id=empresa.id),
            Cargo(nombre="Técnico de Mantenimiento", area_id=areas[0].id, empresa_id=empresa.id),
            Cargo(nombre="Coordinador SST",          area_id=areas[1].id, empresa_id=empresa.id),
            Cargo(nombre="Asistente Administrativo", area_id=areas[1].id, empresa_id=empresa.id),
            Cargo(nombre="Auxiliar de Bodega",       area_id=areas[2].id, empresa_id=empresa.id),
        ]
        for cargo in cargos:
            db.add(cargo)
        db.flush()

        print("Creando usuarios demo...")
        # Contraseña para todos los usuarios demo: demo123
        pwd = get_password_hash("demo123")

        usuarios = [
            User(
                nombre="Carlos SST Demo",
                email="sst@pisst.demo",
                password_hash=pwd,
                role=RoleEnum.sst,
                empresa_id=empresa.id,
                area_id=areas[1].id,
                cargo_id=cargos[2].id
            ),
            User(
                nombre="María Gerencia Demo",
                email="gerencia@pisst.demo",
                password_hash=pwd,
                role=RoleEnum.gerencia,
                empresa_id=empresa.id,
                area_id=areas[1].id,
                cargo_id=cargos[3].id
            ),
            User(
                nombre="Pedro Empleado Demo",
                email="empleado@pisst.demo",
                password_hash=pwd,
                role=RoleEnum.empleado,
                empresa_id=empresa.id,
                area_id=areas[0].id,
                cargo_id=cargos[0].id
            ),
        ]
        for usuario in usuarios:
            db.add(usuario)

        db.commit()
        print("✅ Seed completado exitosamente.")
        print("")
        print("Usuarios demo creados:")
        print("  SST:      sst@pisst.demo      / demo123")
        print("  Gerencia: gerencia@pisst.demo  / demo123")
        print("  Empleado: empleado@pisst.demo  / demo123")

    except Exception as e:
        db.rollback()
        print(f"❌ Error en seed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()