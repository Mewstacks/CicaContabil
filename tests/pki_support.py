"""PFX de teste com o CNPJ no campo ICP-Brasil, sem tocar em certificado real."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import BestAvailableEncryption, pkcs12
from cryptography.x509.oid import NameOID, ObjectIdentifier

ICP_BRASIL_CNPJ_OID = "2.16.76.1.3.3"


def make_pfx(
    *,
    password: str,
    cnpj: str,
    valid_days: int = 365,
    starts_in_days: int = -1,
    include_cnpj: bool = True,
    with_key: bool = True,
) -> bytes:
    """Gera um A1 autoassinado. `valid_days` negativo produz certificado vencido."""

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    # Um e-CNPJ real traz "RAZAO SOCIAL:CNPJ" no CN e o CNPJ no OID 2.16.76.1.3.3 do SAN;
    # o contexto TLS do ADN lê o CN, a importação de lote lê o SAN.
    common_name = f"ESCRITORIO TESTE:{cnpj}" if include_cnpj else "ESCRITORIO TESTE A1"
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.now(UTC)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now + timedelta(days=starts_in_days))
        .not_valid_after(now + timedelta(days=valid_days))
    )
    if include_cnpj:
        builder = builder.add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.OtherName(
                        ObjectIdentifier(ICP_BRASIL_CNPJ_OID),
                        b"\x13\x0e" + cnpj.encode("ascii"),
                    )
                ]
            ),
            critical=False,
        )
    certificate = builder.sign(key, hashes.SHA256())
    return pkcs12.serialize_key_and_certificates(
        b"escritorio",
        key if with_key else None,
        certificate,
        None,
        BestAvailableEncryption(password.encode()),
    )
