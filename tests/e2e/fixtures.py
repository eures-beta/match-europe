"""Local TLS Albert stand-in. No internet, live API key or outbound email."""

from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import ssl

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

ROOT = Path('/artifacts')
SOURCE = (
    'Fictional Example SARL recruits an industrial electrician.\n'
    'Work location: Metz, France.\n'
    'Permanent contract. Full time: 35 hours per week.\n'
    'Tasks: maintain electrical equipment and repair industrial machines.\n'
    'Required experience: 2 years. Electrical qualification required.\n'
    'French B1 desired. Salary: 2500 EUR gross per month.'
)
RESULT = {
    'occupation': 'industrial electrician',
    'specialization': None,
    'companyName': 'Fictional Example SARL',
    'city': 'Metz',
    'contractType': 'PERMANENT_CONTRACT',
    'contractEvidence': 'Permanent contract',
    'missions': ['maintain electrical equipment and repair industrial machines'],
    'profile': ['Electrical qualification required'],
    'experience': 'Required experience: 2 years',
    'hours': '35 hours per week',
    'salary': '2500 EUR gross per month',
}


def certificate():
    path = ROOT / 'tls'
    path.mkdir(parents=True, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Isolated E2E')])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName('web'),
                    x509.DNSName('albert.api.etalab.gouv.fr'),
                ]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    (path / 'cert.pem').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    (path / 'key.pem').write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    (path / 'key.pem').chmod(0o600)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_POST(self):
        length = int(self.headers.get('Content-Length', '0'))
        if self.path != '/v1/chat/completions' or not 0 < length < 100000:
            self.send_error(400)
            return
        payload = json.loads(self.rfile.read(length))
        if (
            self.headers.get('Authorization') != 'Bearer fictional-e2e-key'
            or payload.get('stream') is not False
            or payload.get('response_format') != {'type': 'json_object'}
            or 'Fictional Example SARL' not in json.dumps(payload.get('messages'))
        ):
            self.send_error(400)
            return
        count = ROOT / 'albert-calls.json'
        count.write_text(
            json.dumps({'calls': json.loads(count.read_text())['calls'] + 1})
        )
        response = json.dumps(
            {
                'choices': [
                    {
                        'finish_reason': 'stop',
                        'message': {'content': json.dumps(RESULT)},
                    }
                ]
            }
        ).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)


def main():
    certificate()
    (ROOT / 'mail').mkdir(exist_ok=True)
    (ROOT / 'albert-calls.json').write_text('{"calls": 0}')
    server = HTTPServer(('0.0.0.0', 443), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(ROOT / 'tls/cert.pem', ROOT / 'tls/key.pem')
    server.socket = context.wrap_socket(server.socket, server_side=True)
    (ROOT / 'fixture-ready').touch()
    server.serve_forever()


if __name__ == '__main__':
    main()
