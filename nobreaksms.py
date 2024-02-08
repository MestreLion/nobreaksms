# This file is part of NobreakSMS, see <https://github.com/MestreLion/nobreaksms>
# Copyright (C) 2024 Rodrigo Silva (MestreLion) <linux@rodrigosilva.com>
# License: GPLv3 or later, at your choice. See <http://www.gnu.org/licenses/gpl>
"""
Nobreak SMS monitoring and control via USB
"""

import argparse
import json
import logging
import struct
import sys
import typing as t

import serial

USB_TIMEOUT = 1
USB_DEVICE = "/dev/ttyUSB0"

log = logging.getLogger(__name__)


class NobreakSMS:
    NUM_ARGS = 4
    STATUS_TYPE = {
        "=": "UPS Line Interative",
        ">": "On Line Interative",
        "<": "UPS On Line",
    }
    STATUS_FIELDS = {
        "Tipo":                     (1,  1, chr),
        "UltimaTensao":             (2, 10, float),  # Seems to be always 0
        "TensaoEntrada":            (2, 10, float),
        "TensaoSaida":              (2, 10, float),
        "PotenciaSaida":            (2, 10, float),  # Load percentage
        "FrequenciaSaida":          (2, 10, float),
        "PorcentagemTensaoBateria": (2, 10, float),  # (2, 1, int) by the spec
        "Temperatura":              (2, 10, float),
        "EstadoBateria":            (1,  1, int),    # Bitmap for flags below
    }
    STATUS_FLAGS = (
        "BeepLigado",     # Beep is set to trigger, not necessarily beeping now
        "ShutdownAtivo",  # Shutdown timer active
        "TesteAtivo",     # Battery is being tested
        "UpsOk",          # Battery health
        "Boost",          # Output power ("PotenciaSaida") > 90% (hardcoded)
        "ByPass",         # Output connected to input, bypassing line regulation
        "BateriaBaixa",   # Battery charge < 30% ?
        "BateriaLigada",  # Battery output, either due to battery test or input outage
    )
    assert len(STATUS_FLAGS) == STATUS_FIELDS["EstadoBateria"][0] * 8

    INFO_FIELDS = {
        "Modelo": 12,
        "Versao":  3,
    }
    FEATURE_FIELDS = {
        "FaixaTensao":   7,  # Nominal Input/Output Voltage specs (Bivolt, 115, etc)
        "FaixaCorrente": 3,  # Seems to be always "000"
        "TensaoBateria": 3,  # Nominal battery voltage
        "Frequencia":    2,  # Nominal Input/Output frequency
    }

    STRUCT_FMT = {
        1: "B",
        2: "H",
        4: "I",
    }

    def __init__(self, device=USB_DEVICE, timeout=USB_TIMEOUT):
        self.serial = serial.Serial(
            device,
            baudrate=2400,
            parity=serial.PARITY_NONE,     # default
            stopbits=serial.STOPBITS_ONE,  # default
            bytesize=serial.EIGHTBITS,     # default
            timeout=timeout
        )
        log.debug(self.serial)

    def status(self) -> dict:
        """MedidoresEstado: Resgata medidores e status do UPS"""
        # <!-- Pattern: ‘Q’ Xh Xh Xh Xh CK <CR> -->
        # <!-- Pattern: H ZH ZL MH ML PH PL QH QL RH RL SH SL TH TL Bh CK <CR>
        # <param name="Tipo" size="2" type="hexaString"/>
        # 		<!-- validvalues="[\x3C|\x3D|\x3E]"/> -->
        # 		<!-- Value: \x3C	-> Sinal de menor que "<"
        # 			 Value: \x3D	-> Sinal de igual "="
        # 			 Value: \x3E	-> Sinal de maior que ">" -->
        # if      (bean.getTipo().equals("=")) {bean.setTipo("UPS Line Interative");}
        # else if (bean.getTipo().equals(">")) {bean.setTipo("On Line Interative");}
        # else if (bean.getTipo().equals("<")) {bean.setTipo("UPS On Line");
        # <param name="UltimaTensao"		size="4" type="hexa" calc="{UltimaTensao}/10"/>
        # <param name="TensaoEntrada"		size="4" type="hexa" calc="{TensaoEntrada}/10"/>
        # <param name="TensaoSaida"			size="4" type="hexa" calc="{TensaoSaida}/10"/>
        # <param name="PotenciaSaida"		size="4" type="hexa" calc="{PotenciaSaida}/10"/>
        # <param name="FrequenciaSaida"		size="4" type="hexa" calc="{FrequenciaSaida}/10"/>
        # <param name="PorcentagemTensaoBateria"	size="4" type="hexa" />
        # <param name="Temperatura"			size="4" type="hexa" calc="{Temperatura}/10"/>
        # <param name="EstadoBateria"		size="2" type="binary" ignore="true"/>
        # <!-- O EstadoBateria não será carregado no bean, portanto tem o atributo ignore="true"
        # 	 este servirá para o cálculo dos outros atrobutos -->
        # <param name="BeepLigado"		size="1" type="boolean" start="7" refs="EstadoBateria"/>
        # <param name="ShutdownAtivo"	size="1" type="boolean" start="6" refs="EstadoBateria"/>
        # <param name="TesteAtivo"		size="1" type="boolean" start="5" refs="EstadoBateria"/>
        # <param name="UpsOk"			size="1" type="boolean" start="4" refs="EstadoBateria"/>
        # <param name="Boost"			size="1" type="boolean" start="3" refs="EstadoBateria"/>
        # <param name="ByPass"			size="1" type="boolean" start="2" refs="EstadoBateria"/>
        # <param name="BateriaBaixa"	size="1" type="boolean" start="1" refs="EstadoBateria"/>
        # <param name="BateriaLigada"	size="1" type="boolean" start="0" refs="EstadoBateria"/>
        data = self._unpack_values(self.send_command("Q"), self.STATUS_FIELDS)
        log.debug(data)
        # Add friendly type name
        data["TipoNome"] = self.STATUS_TYPE.get(data["Tipo"], "")
        # Parse flags
        for i, flag in enumerate(self.STATUS_FLAGS):
            data[flag] = bool(data["EstadoBateria"] & 1 << i)
        del data["EstadoBateria"]
        return data

    def info(self) -> dict:
        """Informacoes: Resgata informações do UPS"""
        # <!-- Pattern: ‘I’ Xh Xh Xh Xh CK <CR> -->
        # <!-- Pattern: H M M M M M M M M M M M M V V V CK <CR> -->
        # <param name="Modelo"	size="24" type="string" />
        # <param name="Versao"	size="6" type="string" />
        return self._unpack_strings(self.send_command("I"), self.INFO_FIELDS, header=b'?:')

    def features(self) -> dict:
        """Caracteristicas: Resgata características do UPS"""
        # <!-- Pattern: ‘F’ Xh Xh Xh Xh CK <CR> -->
        # <!-- Pattern: H M M M M M M M Q Q Q S S S R R CK <CR> -->
        # <param name="FaixaTensao"	size="14" type="string" />
        # <param name="FaixaCorrente"	size="6"  type="string" />
        # <param name="TensaoBateria"	size="6"  type="string" />
        # <param name="Frequencia"	size="4"  type="string" />
        data = self._unpack_strings(self.send_command("F"), self.FEATURE_FIELDS)
        log.debug(data)
        # Add friendly nominal voltages
        if data["FaixaTensao"][0] == "E" and "S" in data["FaixaTensao"]:
            vi, _, vo = data["FaixaTensao"][1:].partition("S")
            data["TensaoNominalEntrada"] = vi.replace("Bi", "Bivolt")
            data["TensaoNominalSaida"] = vo.replace("Bi", "Bivolt")
        # Convert some numeric strings to int (not in spec)
        for field in ("TensaoBateria", "Frequencia"):
            data[field] = int(data[field])
        return data

    def toggle_beep(self) -> None:
        """MudaBeep: Muda o beep"""
        # <!-- Pattern: ‘M’ Xh Xh Xh Xh CK <CR> -->
        self.send_command("M")

    def test_battery_until_low(self) -> None:
        """TesteBateriaBaixa: Teste até bateria baixa"""
        # <!-- Pattern: ‘L’ Xh Xh Xh Xh CK <CR> -->
        self.send_command("L")

    def test_battery_minutes(self, minutes: int) -> None:
        self.test_battery(minutes * 60)

    def test_battery_ten_seconds(self) -> None:
        self.test_battery(10)

    # In PowerView, both Mobile and Desktop/Web, this method is only called with
    # whole minutes (up to 99) or 10 seconds. Any other combination is NOT part
    # of the official API. But it does seem to work with all 00:10 - 99:59 range.
    # Relevant references for battery test methods:
    # sms.war/WEB-INF/lib/pv_cliente_web.jar/br.com.sms.powerview.iface.action.DispararEventoAction
    # pv_servidor.jar/br.com.sms.powerview.estadonobreak.NobreakMonofasico
    def test_battery(self, seconds: int) -> None:
        """TestePorSegundos: Teste por 'n' segundos"""
        # <!-- Pattern: ‘T’ NH NL Xh Xh CK <CR> -->
        mins, secs = divmod(seconds, 60)
        arg = (mins * 100 + int(str(secs), 16)).to_bytes(2, "big")
        self.send_command("T", arg, b'\0\0')

    def shutdown(self, seconds: int) -> None:
        """ShutdownPorSegundos: Shutdown em n segundos"""
        # <!-- Pattern: ‘S’SH SL Xh Xh CK <CR> -->
        raise NotImplementedError

    def shutdown_restore(self, *args) -> None:
        """ShutdownRestore: Shutdown e restore"""
        # <!-- Pattern: ‘R’ SH SL RH RL CK <CR> -->
        raise NotImplementedError

    def cancel_test(self) -> None:
        """CancelarTeste: Cancelamento de Teste"""
        # <!-- Pattern: ‘D’ Xh Xh Xh Xh CK <CR> -->
        self.send_command("D")

    def cancel_shutdown_restore(self) -> None:
        """"CancelarShutdownRestore: Cancelamento de Shutdown ou restore"""
        # <!-- Pattern: ‘C’ Xh Xh Xh Xh CK <CR> -->
        self.send_command("C")

    def send_command(self, command: str, *args: bytes) -> bytes:
        # INPUT : CMD ARGS... CHECKSUM <CR>
        # OUTPUT: HEADER DATA... CHECKSUM <CR>
        assert len(command) == 1, "command must be a single character"
        cmd = bytes(command, "ascii") + b''.join(args).ljust(self.NUM_ARGS, b'\xFF')
        data = b''.join((cmd, self._checksum(cmd), serial.CR))
        res = self.send_raw(data)
        if not res:
            return res
        assert len(res) >= 3 and res[-1:] == serial.CR, f"malformed response: {res!r}"
        checksum = res[-2:-1]  # or bytes([res[-2]])
        expected = self._checksum(res[:-2])
        assert checksum == expected, f"bad checksum: {checksum} != {expected}"
        return res[:-2]

    def send_raw(self, data: bytes) -> bytes:
        log.debug("SEND: %r", data)
        self.serial.write(data)
        response = self.serial.read_until(serial.CR, 32)
        log.debug("RECV: %r", response)
        return response

    @staticmethod
    def _checksum(data: bytes) -> bytes:
        return ((sum(data) * 255) & 0xFF).to_bytes(1, "big")

    @staticmethod
    def _unpack_strings(data: bytes, fields: dict, header: bytes = b'') -> dict:
        lengths = fields.values()
        assert len(data) == 1 + sum(lengths), f"data length mismatch: {data}"
        if header:
            assert data[0] in header, f"bad header: {data[:1]} != {header}"
        return {
            field: value.decode("ascii").strip() for field, value in
            zip(fields, struct.unpack("".join(f"{_}s" for _ in lengths), data[1:]))
        }

    @classmethod
    def _unpack_values(cls, data: bytes, fields: dict) -> dict:
        lengths, divs, classes = zip(*fields.values())
        chars = "".join(cls.STRUCT_FMT.get(_, f"{_}x") for _ in lengths)
        assert len(data) == sum(lengths), f"data length mismatch: {data}"
        return {
            field: func(value / div if div > 1 else value)
            for field, value, div, func in
            zip(
                fields,
                struct.unpack(">" + chars, data),
                divs,
                classes,
            )
        }

    def __del__(self):
        if hasattr(self, "serial"):
            self.serial.close()


def show(obj):
    print(json.dumps(obj, indent=4, sort_keys=True))


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-q",
        "--quiet",
        dest="loglevel",
        const=logging.WARNING,
        default=logging.INFO,
        action="store_const",
        help="Suppress informative messages.",
    )
    group.add_argument(
        "-v",
        "--verbose",
        dest="loglevel",
        const=logging.DEBUG,
        action="store_const",
        help="Verbose mode, output extra info.",
    )

    parser.add_argument(
        "-d", "--device", default=USB_DEVICE, help="USB device [Default: %(default)s]"
    )
    parser.add_argument(
        nargs="?", dest="cmd", metavar="COMMAND", help="Optional raw command to send"
    )
    parser.add_argument(
        nargs="*", dest="args", type=int, metavar="ARG",
        help="Raw command arguments (in decimal)",
    )

    args = parser.parse_args(argv)
    args.debug = args.loglevel == logging.DEBUG
    return args


def main(argv: t.Optional[t.List[str]] = None):
    args = parse_args(argv)
    logging.basicConfig(level=args.loglevel, format="%(levelname)-5.5s: %(message)s")
    log.debug(args)

    ups = NobreakSMS(device=args.device)
    show(ups.info())
    show(ups.features())
    if args.cmd:
        res = ups.send_command(args.cmd.upper(), *(_.to_bytes(1, "big") for _ in args.args))
        if res:
            print(res)
    # Show status after command, if any, so it reflects any changes
    show(ups.status())


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except serial.SerialException as e:
        log.error(e)
        if e.errno == 13:
            log.info("Are you in 'dialout' group?")
    except KeyboardInterrupt:
        log.info("Aborting")
        sys.exit(2)
