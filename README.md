Nobreak SMS monitoring and management via USB
=============================================

```sh
git clone https://github.com/MestreLion/nobreaksms.git
cd nobreaksms && python3 -m venv venv && source venv/bin/activate
pip3 install -r requirements.txt
```

```console
(venv) you@home ~ $ python nobreaksms.py  # basic use, for monitoring
```
```json
{
    "Modelo": "PRO700BiBiW",
    "Versao": "1.0"
}
{
    "FaixaCorrente": "000",
    "FaixaTensao": "EBiS115",
    "Frequencia": 60,
    "TensaoBateria": 12,
    "TensaoNominalEntrada": "Bivolt",
    "TensaoNominalSaida": "115"
}
{
    "BateriaBaixa": false,
    "BateriaLigada": false,
    "BeepLigado": true,
    "Boost": false,
    "ByPass": true,
    "FrequenciaSaida": 59.8,
    "PorcentagemTensaoBateria": 34.0,
    "PotenciaSaida": 7.2,
    "ShutdownAtivo": false,
    "Temperatura": 34.5,
    "TensaoEntrada": 120.6,
    "TensaoSaida": 120.6,
    "TesteAtivo": false,
    "Tipo": "=",
    "TipoNome": "UPS Line Interative",
    "UltimaTensao": 0.0,
    "UpsOk": true
}
```

```console
you@home ~ $ python nobreaksms.py --help
usage: nobreaksms.py [-h] [-q | -v] [-d DEVICE] [COMMAND] [ARG [ARG ...]]

Nobreak SMS monitoring and control via USB

positional arguments:
  COMMAND               Optional raw command to send
  ARG                   Raw command arguments (in decimal)

optional arguments:
  -h, --help            show this help message and exit
  -q, --quiet           Suppress informative messages.
  -v, --verbose         Verbose mode, output extra info.
  -d DEVICE, --device DEVICE
                        USB device [Default: /dev/ttyUSB0]
you@home ~ $ python nobreaksms.py -v --device /dev/ttyS8  # Debug mode, different USB port
DEBUG: Namespace(args=[], cmd=None, debug=True, device='/dev/ttyS8', loglevel=10)
DEBUG: Serial<id=0x7fc0a01154f0, open=True>(port='/dev/ttyS8', baudrate=2400, bytesize=8, parity='N', stopbits=1, timeout=1, xonxoff=False, rtscts=False, dsrdtr=False)
DEBUG: SEND: b'I\xff\xff\xff\xff\xbb\r'
DEBUG: RECV: b':PRO700BiBiW 1.0\xe2\r'
{
    "Modelo": "PRO700BiBiW",
    "Versao": "1.0"
}
DEBUG: SEND: b'F\xff\xff\xff\xff\xbe\r'
DEBUG: RECV: b';EBiS115000 1260r\r'
DEBUG: {'FaixaTensao': 'EBiS115', 'FaixaCorrente': '000', 'TensaoBateria': '12', 'Frequencia': '60'}
{
    "FaixaCorrente": "000",
    "FaixaTensao": "EBiS115",
    "Frequencia": 60,
    "TensaoBateria": 12,
    "TensaoNominalEntrada": "Bivolt",
    "TensaoNominalSaida": "115"
}
DEBUG: SEND: b'Q\xff\xff\xff\xff\xb3\r'
DEBUG: RECV: b'=\x00\x00\x04\xb6\x04\xb6\x00H\x02W\x01\xcc\x01W)`\r'
DEBUG: {'Tipo': '=', 'UltimaTensao': 0.0, 'TensaoEntrada': 120.6, 'TensaoSaida': 120.6, 'PotenciaSaida': 7.2, 'FrequenciaSaida': 59.9, 'PorcentagemTensaoBateria': 46.0, 'Temperatura': 34.3, 'EstadoBateria': 41}
{
    "BateriaBaixa": false,
    "BateriaLigada": false,
    "BeepLigado": true,
    "Boost": false,
    "ByPass": true,
    "FrequenciaSaida": 59.9,
    "PorcentagemTensaoBateria": 46.0,
    "PotenciaSaida": 7.2,
    "ShutdownAtivo": false,
    "Temperatura": 34.3,
    "TensaoEntrada": 120.6,
    "TensaoSaida": 120.6,
    "TesteAtivo": false,
    "Tipo": "=",
    "TipoNome": "UPS Line Interative",
    "UltimaTensao": 0.0,
    "UpsOk": true
}
you@home ~ $ python nobreaksms.py T 0 16  # Test battery for 10 seconds
{
    "BateriaBaixa": false,
    "BateriaLigada": true,
    "BeepLigado": true,
    "Boost": false,
    "ByPass": false,
    "FrequenciaSaida": 59.9,
    "PorcentagemTensaoBateria": 100.0,
    "PotenciaSaida": 7.8,
    "ShutdownAtivo": false,
    "Temperatura": 34.5,
    "TensaoEntrada": 121.2,
    "TensaoSaida": 116.8,
    "TesteAtivo": true,
    "Tipo": "=",
    "TipoNome": "UPS Line Interative",
    "UltimaTensao": 0.0,
    "UpsOk": true
}
you@home ~ $ python nobreaksms.py --quiet D  # Cancel test (and suppress output)
you@home ~ $
```
