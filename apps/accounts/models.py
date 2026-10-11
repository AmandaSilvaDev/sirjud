from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("O e-mail é obrigatório.")
        user = self.model(email=self.normalize_email(email).lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Usuário com login por e-mail.

    O acesso a dados de negócio não vem daqui, e sim do vínculo (Membership,
    Fase 1) com uma cooperativa ou um escritório. `is_staff` é reservado ao
    administrador da plataforma. Usuários nunca são apagados, só desativados
    (a auditoria referencia o usuário).
    """

    email = models.EmailField("e-mail", unique=True)
    name = models.CharField("nome", max_length=150)
    phone = models.CharField("telefone", max_length=20, blank=True)
    oab_number = models.CharField("nº OAB", max_length=20, blank=True)
    is_active = models.BooleanField("ativo", default=True)
    is_staff = models.BooleanField("administrador da plataforma", default=False)
    date_joined = models.DateTimeField("cadastrado em", default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"

    def __str__(self):
        return self.name or self.email

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.name.split(" ")[0] if self.name else self.email
