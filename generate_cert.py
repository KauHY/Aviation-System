# 生成自签名SSL证书
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import datetime
import socket
import ipaddress

# 生成私钥
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)

# 获取本机IP
hostname = socket.gethostname()
local_ip = socket.gethostbyname(hostname)

# 创建证书
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, u"CN"),
    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Beijing"),
    x509.NameAttribute(NameOID.LOCALITY_NAME, u"Beijing"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Aviation System"),
    x509.NameAttribute(NameOID.COMMON_NAME, local_ip),
])

cert = x509.CertificateBuilder().subject_name(
    subject
).issuer_name(
    issuer
).public_key(
    private_key.public_key()
).serial_number(
    x509.random_serial_number()
).not_valid_before(
    datetime.datetime.utcnow()
).not_valid_after(
    datetime.datetime.utcnow() + datetime.timedelta(days=365)
).add_extension(
    x509.SubjectAlternativeName([
        x509.DNSName(u"localhost"),
        x509.DNSName(hostname),
        x509.IPAddress(ipaddress.IPv4Address(local_ip)),
    ]),
    critical=False,
).sign(private_key, hashes.SHA256(), default_backend())

# 保存私钥
with open("backend/key.pem", "wb") as f:
    f.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ))

# 保存证书
with open("backend/cert.pem", "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))

print(f"✅ SSL证书已生成！")
print(f"📍 本机IP: {local_ip}")
print(f"🔐 证书文件: backend/cert.pem")
print(f"🔑 私钥文件: backend/key.pem")
print(f"\n⚠️  使用自签名证书时，浏览器会显示安全警告，点击'高级'→'继续访问'即可")
print(f"\n📱 远程访问地址: https://{local_ip}:8000")
