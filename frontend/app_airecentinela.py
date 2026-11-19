"""Frontend de Aire Centinela AI: diagnóstico transparente, perfiles y evidencia por ubicación."""

import json
import os
import sys
from datetime import datetime

import matplotlib.dates as mdates
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ia_engine.motor_ia import (
    PERFILES_USO,
    obtener_diagnostico_completo,
)

RAIZ_PROYECTO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RUTA_CSV = os.path.join(RAIZ_PROYECTO, "data", "datos_ambientales.csv")
RUTA_UBICACIONES = os.path.join(RAIZ_PROYECTO, "data", "sesiones_ubicaciones.json")
COLUMNAS_CSV = ("timestamp", "temperatura", "humedad", "presion", "eco2", "tvoc")
INTERVALO_ACTUALIZACION_MS = 1000

# Paleta Bio-Ambiental Obsidiana & Esmeralda (sin tonos azules)
FONDO = "#0B0D0C"
SIDEBAR = "#111513"
TARJETA = "#161B18"
TARJETA_ALT = "#1E2521"
BORDE = "#2B3530"
TEXTO = "#F4F6F5"
SECUNDARIO = "#9CA8A1"
ACENTO = "#10B981"
LIMA = "#84CC16"
AMBAR = "#F59E0B"
CORAL = "#F43F5E"
VIOLETA = "#A78BFA"

PUNTOS_SAN_MIGUEL = {
    "Campus UGB · San Miguel": ("13.4892° N, 88.1914° O", "San Miguel, El Salvador"),
    "Laboratorio Electrónica · UGB": ("13.4895° N, 88.1911° O", "San Miguel, El Salvador"),
    "Feria de Proyectos · UGB": ("13.4889° N, 88.1917° O", "San Miguel, El Salvador"),
    "Centro Urbano · San Miguel": ("13.4833° N, 88.1833° O", "San Miguel, El Salvador"),
    "Zona Residencial · San Miguel": ("13.4798° N, 88.1865° O", "San Miguel, El Salvador"),
}


def obtener_ubicacion_base() -> dict[str, str]:
    punto_default = "Campus UGB · San Miguel"
    coords, region = PUNTOS_SAN_MIGUEL[punto_default]
    return {
        "nombre": punto_default,
        "region": region,
        "coordenadas": coords,
    }


def inspeccionar_csv() -> tuple[bool, int, str]:
    """Devuelve (existe_con_datos, cantidad_filas, resumen_legible)."""
    if not os.path.exists(RUTA_CSV):
        return False, 0, "No existe data/datos_ambientales.csv todavía."
    try:
        df = pd.read_csv(RUTA_CSV)
        if df.empty:
            return False, 0, "El archivo CSV existe pero está vacío (0 filas aún)."
        ultima = df.iloc[-1]
        temp = pd.to_numeric(ultima.get("temperatura"), errors="coerce")
        eco2 = pd.to_numeric(ultima.get("eco2"), errors="coerce")
        resumen = (
            f"{len(df)} filas en CSV · Última lectura: "
            f"{temp:.1f} °C / {eco2:.0f} ppm ({ultima.get('timestamp', 'sin hora')})"
        )
        return True, len(df), resumen
    except Exception as exc:
        return False, 0, f"Error leyendo CSV: {exc}"


class DialogoArranque(QDialog):
    """Diagnóstico paso a paso con avance manual para que puedas leer qué ocurre."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aire Centinela AI | Diagnóstico Paso a Paso")
        self.setMinimumSize(600, 440)
        self.setStyleSheet(
            f"QDialog {{background-color: {FONDO}; border: 1px solid {BORDE};}}"
            f"QLabel {{color: {TEXTO}; background: transparent;}}"
        )
        self.ubicacion_detectada = obtener_ubicacion_base()
        self.paso = 0
        self._construir_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._siguiente_paso)
        self.timer.start(900)

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 26, 30, 26)
        layout.setSpacing(14)

        marca = QLabel("AIRE CENTINELA AI · AUDITORÍA DE ARRANQUE")
        marca.setStyleSheet(
            f"color: {LIMA}; font-size: 11px; font-weight: 800; letter-spacing: 1.5px;"
        )
        layout.addWidget(marca)

        titulo = QLabel("Estado Real de Datos, Sensores y Motor IA")
        titulo.setStyleSheet(f"color: {TEXTO}; font-size: 20px; font-weight: 800;")
        layout.addWidget(titulo)

        marco = QFrame()
        marco.setStyleSheet(
            f"QFrame {{background-color: {TARJETA}; border: 1px solid {BORDE}; border-radius: 12px;}}"
        )
        v_box = QVBoxLayout(marco)
        v_box.setContentsMargins(18, 16, 18, 16)
        v_box.setSpacing(12)

        self.lbl_paso1 = QLabel("1. Revisando archivo de telemetría CSV...")
        self.lbl_paso2 = QLabel("2. Revisando últimas lecturas de CCS811 (A4/A5) y BME280 (A2/A3)...")
        self.lbl_paso3 = QLabel("3. Evaluando motor Isolation Forest...")
        self.lbl_paso4 = QLabel("4. Ubicación de estación configurada...")

        for lbl in (self.lbl_paso1, self.lbl_paso2, self.lbl_paso3, self.lbl_paso4):
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"color: {SECUNDARIO}; font-size: 12px; border: none;")
            v_box.addWidget(lbl)

        layout.addWidget(marco)

        self.barra = QProgressBar()
        self.barra.setRange(0, 100)
        self.barra.setValue(0)
        self.barra.setTextVisible(True)
        self.barra.setFormat("Diagnóstico: %p%")
        self.barra.setFixedHeight(18)
        self.barra.setStyleSheet(
            f"QProgressBar {{background-color: {TARJETA}; color: {TEXTO}; border: 1px solid {BORDE}; "
            "border-radius: 6px; font-size: 11px; text-align: center;}}"
            f"QProgressBar::chunk {{background-color: {ACENTO}; border-radius: 5px;}}"
        )
        layout.addWidget(self.barra)

        self.lbl_ayuda = QLabel(
            "Si el CSV está vacío, revisa en la terminal si el backend está recibiendo JSON o si el firmware reporta FALLO."
        )
        self.lbl_ayuda.setWordWrap(True)
        self.lbl_ayuda.setStyleSheet(f"color: {SECUNDARIO}; font-size: 12px;")
        layout.addWidget(self.lbl_ayuda)

        fila_btns = QHBoxLayout()
        self.btn_reintentar = QPushButton("Volver a Comprobar")
        self.btn_reintentar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reintentar.setStyleSheet(
            f"QPushButton {{background-color: {TARJETA_ALT}; color: {TEXTO}; border: 1px solid {BORDE}; "
            "padding: 8px 14px; border-radius: 8px; font-size: 12px; font-weight: 700;}}"
        )
        self.btn_reintentar.clicked.connect(self._reiniciar_diagnostico)
        fila_btns.addWidget(self.btn_reintentar)

        fila_btns.addStretch()

        self.btn_entrar = QPushButton("Abrir Consola")
        self.btn_entrar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_entrar.setStyleSheet(
            f"QPushButton {{background-color: {ACENTO}; color: #05140E; font-weight: 800; "
            "padding: 9px 20px; border-radius: 8px; font-size: 13px;}}"
            "QPushButton:hover {background-color: #34D399;}"
        )
        self.btn_entrar.clicked.connect(self.accept)
        fila_btns.addWidget(self.btn_entrar)
        layout.addLayout(fila_btns)

    def _reiniciar_diagnostico(self):
        self.paso = 0
        self.barra.setValue(0)
        self.lbl_paso1.setText("1. Revisando archivo de telemetría CSV...")
        self.lbl_paso2.setText("2. Revisando últimas lecturas de CCS811 y BME280...")
        self.lbl_paso3.setText("3. Evaluando motor Isolation Forest...")
        self.timer.start(800)

    def _siguiente_paso(self):
        self.paso += 1
        tiene_datos, n_filas, resumen = inspeccionar_csv()

        if self.paso == 1:
            self.barra.setValue(25)
            if tiene_datos:
                self.lbl_paso1.setText(f"1. [OK] {resumen}")
                self.lbl_paso1.setStyleSheet(f"color: {ACENTO}; font-size: 12px; border: none;")
            else:
                self.lbl_paso1.setText(f"1. [ATENCIÓN] {resumen}")
                self.lbl_paso1.setStyleSheet(f"color: {AMBAR}; font-size: 12px; border: none;")

        elif self.paso == 2:
            self.barra.setValue(50)
            if tiene_datos:
                self.lbl_paso2.setText(
                    "2. [OK] Tramas numéricas detectadas en CSV (CCS811 A4/A5 y BME280 A2/A3)."
                )
                self.lbl_paso2.setStyleSheet(f"color: {ACENTO}; font-size: 12px; border: none;")
            else:
                self.lbl_paso2.setText(
                    "2. [SIN LECTURAS] Aún no llegan filas válidas. Si usas hardware, revisa la consola del backend."
                )
                self.lbl_paso2.setStyleSheet(f"color: {CORAL}; font-size: 12px; border: none;")

        elif self.paso == 3:
            self.barra.setValue(75)
            diag = obtener_diagnostico_completo(RUTA_CSV)
            nivel = diag.get("nivel_alerta", "SIN_DATOS")
            msg = diag.get("mensaje", "")
            color_ia = ACENTO if nivel == "OPTIMO" else (AMBAR if nivel in ("CALIBRANDO", "PRECAUCION") else CORAL)
            self.lbl_paso3.setText(f"3. Motor IA -> {nivel}: {msg}")
            self.lbl_paso3.setStyleSheet(f"color: {color_ia}; font-size: 12px; border: none;")

        elif self.paso >= 4:
            self.timer.stop()
            self.barra.setValue(100)
            self.lbl_paso4.setText(
                f"4. [LISTO] {self.ubicacion_detectada['nombre']} ({self.ubicacion_detectada['coordenadas']})"
            )
            self.lbl_paso4.setStyleSheet(f"color: {ACENTO}; font-size: 12px; border: none;")
            self.lbl_ayuda.setText(
                f"Diagnóstico pausado para tu lectura ({n_filas} filas listas). Pulsa 'Abrir Consola' cuando gustes."
            )


class TarjetaMetrica(QFrame):
    def __init__(self, titulo, unidad, color, decimales=1, destacada=False):
        super().__init__()
        self.decimales = decimales
        self.setMinimumHeight(152)
        self.setStyleSheet(
            f"QFrame {{background-color: {TARJETA}; border: 1px solid "
            f"{ACENTO if destacada else BORDE}; border-radius: 14px;}}"
            "QLabel {border: none; background: transparent;}"
        )

        contenedor = QVBoxLayout(self)
        contenedor.setContentsMargins(18, 14, 18, 14)
        contenedor.setSpacing(6)

        etiqueta = QLabel(titulo.upper())
        etiqueta.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: 800; letter-spacing: 1px;"
        )
        contenedor.addWidget(etiqueta)

        fila_valor = QHBoxLayout()
        fila_valor.setSpacing(8)
        fila_valor.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.etiqueta_valor = QLabel("—")
        self.etiqueta_valor.setStyleSheet(
            f"color: {LIMA if destacada else TEXTO}; "
            f"font-size: {34 if destacada else 28}px; font-weight: 800;"
        )
        fila_valor.addWidget(self.etiqueta_valor)

        etiqueta_unidad = QLabel(unidad)
        etiqueta_unidad.setStyleSheet(f"color: {SECUNDARIO}; font-size: 13px; font-weight: 600;")
        fila_valor.addWidget(etiqueta_unidad)
        contenedor.addLayout(fila_valor)

        self.etiqueta_interpretacion = QLabel("Esperando lectura válida...")
        self.etiqueta_interpretacion.setWordWrap(True)
        self.etiqueta_interpretacion.setStyleSheet(f"color: {SECUNDARIO}; font-size: 12px;")
        contenedor.addWidget(self.etiqueta_interpretacion)
        contenedor.addStretch()

    def actualizar(self, valor, interpretacion: str = ""):
        numero = pd.to_numeric(valor, errors="coerce")
        if pd.isna(numero):
            self.etiqueta_valor.setText("—")
        else:
            self.etiqueta_valor.setText(f"{float(numero):.{self.decimales}f}")
        if interpretacion:
            self.etiqueta_interpretacion.setText(interpretacion)


class GraficaECO2(FigureCanvasQTAgg):
    def __init__(self, altura_min=260):
        self.figura = Figure(figsize=(10, 3.5), dpi=100, facecolor=TARJETA)
        self.ejes = self.figura.add_subplot(111)
        super().__init__(self.figura)
        self.setMinimumHeight(altura_min)
        self.mostrar_mensaje("Esperando lecturas válidas de eCO2...")

    def _preparar_ejes(self):
        self.ejes.clear()
        self.ejes.set_facecolor(TARJETA)
        self.ejes.tick_params(colors=SECUNDARIO, labelsize=9)
        self.ejes.set_ylabel("eCO2 (ppm)", color=SECUNDARIO, fontsize=10)
        self.ejes.set_xlabel("Hora", color=SECUNDARIO, fontsize=10)
        self.ejes.grid(True, color=BORDE, linestyle="--", linewidth=0.7, alpha=0.7)
        self.ejes.set_axisbelow(True)
        for borde in self.ejes.spines.values():
            borde.set_color(BORDE)

    def mostrar_mensaje(self, mensaje):
        self._preparar_ejes()
        self.ejes.text(
            0.5,
            0.5,
            mensaje,
            transform=self.ejes.transAxes,
            ha="center",
            va="center",
            color=SECUNDARIO,
            fontsize=11,
        )
        self.figura.tight_layout(pad=1.8)
        self.draw_idle()

    def actualizar(self, datos_csv, base_eco2: float = 450.0, limite_normal: float = 650.0):
        reciente = datos_csv.tail(120)
        historico = pd.DataFrame(
            {
                "fecha": pd.to_datetime(reciente["timestamp"], errors="coerce"),
                "eco2": pd.to_numeric(reciente["eco2"], errors="coerce"),
            }
        ).dropna()
        historico = historico[historico["eco2"] > 0].sort_values("fecha")

        if historico.empty:
            self.mostrar_mensaje("Sin lecturas válidas de eCO2 en el historial aún.")
            return

        self._preparar_ejes()
        fechas = historico["fecha"].tolist()
        valores = historico["eco2"].to_numpy()

        piso_banda = max(380.0, base_eco2 - 80.0)
        self.ejes.axhspan(
            piso_banda,
            limite_normal,
            color=ACENTO,
            alpha=0.12,
            label=f"Zona normal ({piso_banda:.0f}–{limite_normal:.0f} ppm)",
        )
        self.ejes.axhline(
            limite_normal,
            color=AMBAR,
            linestyle=":",
            linewidth=1.2,
            alpha=0.9,
            label="Umbral preventivo",
        )
        self.ejes.plot(
            fechas,
            valores,
            color=LIMA,
            linewidth=2.3,
            marker="o" if len(historico) <= 55 else None,
            markersize=3.5,
            label="eCO2 (ppm)",
        )
        self.ejes.legend(
            loc="upper left",
            facecolor=SIDEBAR,
            edgecolor=BORDE,
            labelcolor=TEXTO,
            fontsize=8.5,
        )

        localizador = mdates.AutoDateLocator(minticks=3, maxticks=8)
        self.ejes.xaxis.set_major_locator(localizador)
        self.ejes.xaxis.set_major_formatter(mdates.ConciseDateFormatter(localizador))
        self.ejes.margins(x=0.02, y=0.18)
        self.figura.tight_layout(pad=1.8)
        self.draw_idle()


class VentanaAireCentinela(QMainWindow):
    def __init__(self, ubicacion_inicial: dict[str, str]):
        super().__init__()
        self.ubicacion_actual = ubicacion_inicial
        self.ultimo_diagnostico: dict = {}
        self.ultimo_df: pd.DataFrame = pd.DataFrame()
        self.sesiones_guardadas: list[dict] = self._cargar_sesiones()

        self.setWindowTitle("Aire Centinela AI | Estación Ambiental")
        self.setMinimumSize(1140, 750)
        self.resize(1300, 820)
        self.setStyleSheet(f"QMainWindow {{background-color: {FONDO};}}")

        self._construir_interfaz()
        self._refrescar_tabla_ubicaciones()
        # Primera lectura inmediata al abrir sin esperar 1 segundo
        QTimer.singleShot(150, self._actualizar_datos)

    def _cargar_sesiones(self) -> list[dict]:
        if not os.path.exists(RUTA_UBICACIONES):
            return []
        try:
            with open(RUTA_UBICACIONES, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []

    def _guardar_sesiones_disco(self):
        os.makedirs(os.path.dirname(RUTA_UBICACIONES), exist_ok=True)
        with open(RUTA_UBICACIONES, "w", encoding="utf-8") as f:
            json.dump(self.sesiones_guardadas, f, ensure_ascii=False, indent=2)

    def _construir_interfaz(self):
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        layout_raiz = QHBoxLayout(widget_central)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(0)

        # Barra lateral
        sidebar = QFrame()
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet(
            f"QFrame {{background-color: {SIDEBAR}; border-right: 1px solid {BORDE};}}"
            "QLabel {border: none; background: transparent;}"
        )
        v_side = QVBoxLayout(sidebar)
        v_side.setContentsMargins(18, 24, 18, 20)
        v_side.setSpacing(10)

        badge_ugb = QLabel("UGB · SAN MIGUEL")
        badge_ugb.setStyleSheet(
            f"color: {LIMA}; font-size: 11px; font-weight: 800; letter-spacing: 1.5px;"
        )
        v_side.addWidget(badge_ugb)

        logo = QLabel("Aire Centinela AI")
        logo.setStyleSheet(f"color: {TEXTO}; font-size: 20px; font-weight: 800;")
        v_side.addWidget(logo)

        v_side.addSpacing(10)

        self.botones_nav = []
        vistas_info = [
            ("1. Monitor en Vivo", 0),
            ("2. Perfiles y Guía", 1),
            ("3. Ubicaciones", 2),
        ]
        for texto_btn, idx in vistas_info:
            btn = QPushButton(texto_btn)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, i=idx: self._cambiar_vista(i))
            v_side.addWidget(btn)
            self.botones_nav.append(btn)

        v_side.addStretch()

        box_gps = QFrame()
        box_gps.setStyleSheet(
            f"QFrame {{background-color: {TARJETA}; border: 1px solid {BORDE}; border-radius: 12px;}}"
        )
        v_gps = QVBoxLayout(box_gps)
        v_gps.setContentsMargins(14, 12, 14, 12)
        v_gps.setSpacing(6)

        lbl_gps_tit = QLabel("UBICACIÓN ACTUAL")
        lbl_gps_tit.setStyleSheet(
            f"color: {LIMA}; font-size: 10px; font-weight: 800; letter-spacing: 1px;"
        )
        v_gps.addWidget(lbl_gps_tit)

        self.combo_puntos = QComboBox()
        self.combo_puntos.addItems(list(PUNTOS_SAN_MIGUEL.keys()) + ["Otro punto..."])
        self.combo_puntos.setStyleSheet(
            f"QComboBox {{background-color: {FONDO}; color: {TEXTO}; border: 1px solid {BORDE}; "
            "border-radius: 6px; padding: 5px 8px; font-size: 12px; font-weight: 600;}}"
            f"QComboBox QAbstractItemView {{background-color: {TARJETA}; color: {TEXTO};}}"
        )
        self.combo_puntos.currentTextChanged.connect(self._al_cambiar_punto_predefinido)
        v_gps.addWidget(self.combo_puntos)

        self.input_ubicacion = QLineEdit(self.ubicacion_actual["nombre"])
        self.input_ubicacion.setStyleSheet(
            f"QLineEdit {{background-color: {FONDO}; color: {TEXTO}; border: 1px solid {BORDE}; "
            "border-radius: 6px; padding: 6px 8px; font-size: 12px;}}"
        )
        v_gps.addWidget(self.input_ubicacion)

        self.lbl_coords = QLabel(
            f"{self.ubicacion_actual['coordenadas']} · {self.ubicacion_actual['region']}"
        )
        self.lbl_coords.setWordWrap(True)
        self.lbl_coords.setStyleSheet(f"color: {SECUNDARIO}; font-size: 11px;")
        v_gps.addWidget(self.lbl_coords)

        btn_guardar_ubi = QPushButton("Guardar Ubicación")
        btn_guardar_ubi.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_guardar_ubi.setStyleSheet(
            f"QPushButton {{background-color: {ACENTO}; color: #05140E; font-weight: 800; "
            "padding: 7px; border-radius: 7px; font-size: 12px;}}"
            "QPushButton:hover {background-color: #34D399;}"
        )
        btn_guardar_ubi.clicked.connect(self._registrar_ubicacion_actual)
        v_gps.addWidget(btn_guardar_ubi)

        v_side.addWidget(box_gps)
        layout_raiz.addWidget(sidebar)

        # Panel derecho
        contenedor_derecho = QWidget()
        v_der = QVBoxLayout(contenedor_derecho)
        v_der.setContentsMargins(24, 20, 24, 20)
        v_der.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(12)

        col_titulo = QVBoxLayout()
        self.lbl_titulo_vista = QLabel("Monitor en Vivo")
        self.lbl_titulo_vista.setStyleSheet(f"color: {TEXTO}; font-size: 22px; font-weight: 800;")
        col_titulo.addWidget(self.lbl_titulo_vista)

        self.lbl_estado_flujo = QLabel("Estado del flujo: comprobando archivo CSV...")
        self.lbl_estado_flujo.setStyleSheet(f"color: {SECUNDARIO}; font-size: 12px;")
        col_titulo.addWidget(self.lbl_estado_flujo)
        header.addLayout(col_titulo)
        header.addStretch()

        lbl_perf = QLabel("Perfil:")
        lbl_perf.setStyleSheet(f"color: {SECUNDARIO}; font-size: 12px; font-weight: 700;")
        header.addWidget(lbl_perf)

        self.combo_perfil = QComboBox()
        self.combo_perfil.addItems(PERFILES_USO)
        self.combo_perfil.setStyleSheet(
            f"QComboBox {{background-color: {TARJETA}; color: {TEXTO}; border: 1px solid {BORDE}; "
            "border-radius: 8px; padding: 7px 12px; font-size: 12px; font-weight: 700; min-width: 170px;}}"
            f"QComboBox QAbstractItemView {{background-color: {TARJETA}; color: {TEXTO};}}"
        )
        self.combo_perfil.currentTextChanged.connect(self._actualizar_panel_perfil)
        header.addWidget(self.combo_perfil)

        btn_recalibrar = QPushButton("Recalibrar Zona")
        btn_recalibrar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_recalibrar.setStyleSheet(
            f"QPushButton {{background-color: {TARJETA_ALT}; color: {LIMA}; border: 1px solid {LIMA}; "
            "border-radius: 8px; padding: 7px 12px; font-size: 12px; font-weight: 700;}}"
            f"QPushButton:hover {{background-color: {BORDE};}}"
        )
        btn_recalibrar.clicked.connect(self._recalibrar_zona)
        header.addWidget(btn_recalibrar)

        self.etiqueta_ia = QLabel("LEYENDO CSV...")
        self.etiqueta_ia.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.etiqueta_ia.setMinimumWidth(310)
        self.etiqueta_ia.setStyleSheet(
            f"background-color: {TARJETA_ALT}; color: {TEXTO}; border: 1px solid {BORDE}; "
            "font-size: 12px; font-weight: 800; border-radius: 10px; padding: 9px 14px;"
        )
        header.addWidget(self.etiqueta_ia)
        v_der.addLayout(header)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._crear_vista_monitor())
        self.stack.addWidget(self._crear_vista_perfiles())
        self.stack.addWidget(self._crear_vista_ubicaciones())
        v_der.addWidget(self.stack, stretch=1)

        layout_raiz.addWidget(contenedor_derecho, stretch=1)

        self._cambiar_vista(0)
        self.temporizador = QTimer(self)
        self.temporizador.timeout.connect(self._actualizar_datos)
        self.temporizador.start(INTERVALO_ACTUALIZACION_MS)

    def _al_cambiar_punto_predefinido(self, seleccion: str):
        if seleccion in PUNTOS_SAN_MIGUEL:
            coords, region = PUNTOS_SAN_MIGUEL[seleccion]
            self.ubicacion_actual = {
                "nombre": seleccion,
                "region": region,
                "coordenadas": coords,
            }
            self.input_ubicacion.setText(seleccion)
            self.lbl_coords.setText(f"{coords} · {region}")
        else:
            self.input_ubicacion.clear()
            self.input_ubicacion.setFocus()

    def _cambiar_vista(self, indice: int):
        self.stack.setCurrentIndex(indice)
        titulos = [
            "Monitor en Vivo",
            "Perfiles de Uso y Guía de Sensores",
            "Historial y Comparativa por Ubicación",
        ]
        self.lbl_titulo_vista.setText(titulos[indice])

        for i, btn in enumerate(self.botones_nav):
            activo = i == indice
            btn.setChecked(activo)
            btn.setStyleSheet(
                f"QPushButton {{text-align: left; padding: 11px 14px; border-radius: 10px; font-size: 13px; "
                f"font-weight: {'800' if activo else '600'}; "
                f"background-color: {TARJETA_ALT if activo else 'transparent'}; "
                f"color: {LIMA if activo else SECUNDARIO}; "
                f"border: 1px solid {ACENTO if activo else 'transparent'};}}"
                f"QPushButton:hover {{color: {TEXTO}; background-color: {TARJETA};}}"
            )

    def _crear_vista_monitor(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        grid = QGridLayout()
        grid.setSpacing(14)

        self.tarjetas = {
            "temperatura": TarjetaMetrica("Temperatura", "°C", CORAL),
            "humedad": TarjetaMetrica("Humedad Relativa", "%", ACENTO),
            "presion": TarjetaMetrica("Presión Atmosférica", "hPa", VIOLETA, decimales=2),
            "eco2": TarjetaMetrica("eCO2 (Calidad de Aire)", "ppm", LIMA, decimales=0, destacada=True),
            "tvoc": TarjetaMetrica("TVOC (Compuestos)", "ppb", AMBAR, decimales=0),
        }

        grid.addWidget(self.tarjetas["temperatura"], 0, 0)
        grid.addWidget(self.tarjetas["humedad"], 0, 1)
        grid.addWidget(self.tarjetas["presion"], 0, 2)
        grid.addWidget(self.tarjetas["eco2"], 1, 0, 1, 2)
        grid.addWidget(self.tarjetas["tvoc"], 1, 2)
        layout.addLayout(grid)

        banner = QFrame()
        banner.setStyleSheet(
            f"QFrame {{background-color: {TARJETA_ALT}; border: 1px solid {BORDE}; border-radius: 12px;}}"
            "QLabel {border: none; background: transparent;}"
        )
        h_banner = QHBoxLayout(banner)
        h_banner.setContentsMargins(16, 10, 16, 10)

        self.lbl_banner_perfil = QLabel("Recomendación del perfil: esperando lecturas...")
        self.lbl_banner_perfil.setWordWrap(True)
        self.lbl_banner_perfil.setStyleSheet(f"color: {TEXTO}; font-size: 12px; font-weight: 600;")
        h_banner.addWidget(self.lbl_banner_perfil)
        layout.addWidget(banner)

        self.grafica = GraficaECO2(altura_min=260)
        layout.addWidget(self.grafica, stretch=1)
        return pagina

    def _crear_vista_perfiles(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea {background: transparent; border: none;}")

        contenido = QWidget()
        contenido.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(contenido)
        layout.setContentsMargins(0, 0, 8, 12)
        layout.setSpacing(18)

        grid_sectores = QGridLayout()
        grid_sectores.setSpacing(14)
        self.tarjetas_sectores: dict[str, tuple[QLabel, QLabel]] = {}

        colores_sector = {
            "Oficina / Escuela": LIMA,
            "Agricultura / Cultivo": ACENTO,
            "Hogar / Salud": AMBAR,
        }

        for col, perfil in enumerate(PERFILES_USO):
            color_sec = colores_sector[perfil]
            card = QFrame()
            card.setMinimumHeight(145)
            card.setStyleSheet(
                f"QFrame {{background-color: {TARJETA}; border: 1px solid {BORDE}; border-radius: 12px;}}"
                "QLabel {border: none; background: transparent;}"
            )
            v = QVBoxLayout(card)
            v.setContentsMargins(18, 16, 18, 16)
            v.setSpacing(8)

            lbl_head = QLabel(perfil.upper())
            lbl_head.setStyleSheet(f"color: {color_sec}; font-size: 12px; font-weight: 800;")
            v.addWidget(lbl_head)

            lbl_estado_sec = QLabel("Esperando datos...")
            lbl_estado_sec.setWordWrap(True)
            lbl_estado_sec.setStyleSheet(f"color: {TEXTO}; font-size: 14px; font-weight: 700;")
            v.addWidget(lbl_estado_sec)

            lbl_detalle_sec = QLabel("Conecta los sensores o espera lecturas válidas.")
            lbl_detalle_sec.setWordWrap(True)
            lbl_detalle_sec.setStyleSheet(f"color: {SECUNDARIO}; font-size: 12px;")
            v.addWidget(lbl_detalle_sec)
            v.addStretch()

            self.tarjetas_sectores[perfil] = (lbl_estado_sec, lbl_detalle_sec)
            grid_sectores.addWidget(card, 0, col)

        layout.addLayout(grid_sectores)

        fichas = [
            ("eCO2 (ppm)", LIMA, "400–650 fresco · 750–1000 moderado · >1200 aire viciado",
             "Mide qué tan renovado está el aire en espacios cerrados."),
            ("TVOC (ppb)", AMBAR, "0–50 puro · 50–220 moderado · >220 alto",
             "Detecta compuestos volátiles, humo, alcohol o aerosoles."),
            ("Temperatura (°C) y Humedad (%)", CORAL, "20–28 °C · 35–65 % RH confort · >78 % RH humedad alta",
             "Indica confort térmico y riesgo de condensación o humedad."),
            ("Presión Atmosférica (hPa)", VIOLETA, "San Miguel (~110 m s. n. m.): ~996–1002 hPa",
             "Muestra la presión local y cambios barométricos."),
            ("Isolation Forest", ACENTO, "Aprende la línea base en 15 lecturas",
             "Detecta anomalías respecto al comportamiento normal de cada lugar."),
        ]

        for titulo_ficha, color_ficha, rango_ficha, desc_ficha in fichas:
            ficha = QFrame()
            ficha.setStyleSheet(
                f"QFrame {{background-color: {TARJETA}; border: 1px solid {BORDE}; "
                f"border-left: 4px solid {color_ficha}; border-radius: 10px;}}"
                "QLabel {border: none; background: transparent;}"
            )
            vf = QVBoxLayout(ficha)
            vf.setContentsMargins(16, 12, 16, 12)
            vf.setSpacing(4)

            fila_sup = QHBoxLayout()
            lbl_tf = QLabel(titulo_ficha)
            lbl_tf.setStyleSheet(f"color: {TEXTO}; font-size: 13px; font-weight: 800;")
            fila_sup.addWidget(lbl_tf)
            fila_sup.addStretch()

            lbl_rf = QLabel(rango_ficha)
            lbl_rf.setStyleSheet(f"color: {color_ficha}; font-size: 11px; font-weight: 700;")
            fila_sup.addWidget(lbl_rf)
            vf.addLayout(fila_sup)

            lbl_df = QLabel(desc_ficha)
            lbl_df.setWordWrap(True)
            lbl_df.setStyleSheet(f"color: {SECUNDARIO}; font-size: 12px;")
            vf.addWidget(lbl_df)
            layout.addWidget(ficha)

        layout.addStretch()
        scroll.setWidget(contenido)
        return scroll

    def _crear_vista_ubicaciones(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        barra_ev = QHBoxLayout()
        lbl_info = QLabel("Haz clic en una fila para ver su análisis guardado y compararlo con la lectura actual.")
        lbl_info.setStyleSheet(f"color: {SECUNDARIO}; font-size: 12px;")
        barra_ev.addWidget(lbl_info)
        barra_ev.addStretch()

        btn_guardar_ahora = QPushButton("Guardar Snapshot Actual")
        btn_guardar_ahora.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_guardar_ahora.setStyleSheet(
            f"QPushButton {{background-color: {ACENTO}; color: #05140E; font-weight: 800; "
            "padding: 8px 14px; border-radius: 8px; font-size: 12px;}}"
        )
        btn_guardar_ahora.clicked.connect(self._registrar_ubicacion_actual)
        barra_ev.addWidget(btn_guardar_ahora)

        btn_eliminar = QPushButton("Eliminar Fila")
        btn_eliminar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_eliminar.setStyleSheet(
            f"QPushButton {{background-color: {TARJETA}; color: {CORAL}; border: 1px solid {CORAL}; "
            "padding: 8px 12px; border-radius: 8px; font-size: 12px; font-weight: 700;}}"
        )
        btn_eliminar.clicked.connect(self._eliminar_ubicacion_seleccionada)
        barra_ev.addWidget(btn_eliminar)
        layout.addLayout(barra_ev)

        self.tabla_ubicaciones = QTableWidget(0, 7)
        self.tabla_ubicaciones.setHorizontalHeaderLabels(
            ["Ubicación", "Fecha y Hora", "Temp (°C)", "Humedad (%)", "eCO2 (ppm)", "Base IA", "Estado"]
        )
        self.tabla_ubicaciones.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_ubicaciones.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_ubicaciones.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_ubicaciones.setMaximumHeight(200)
        self.tabla_ubicaciones.setStyleSheet(
            f"QTableWidget {{background-color: {TARJETA}; color: {TEXTO}; border: 1px solid {BORDE}; "
            "border-radius: 10px; font-size: 12px;}}"
            f"QHeaderView::section {{background-color: {SIDEBAR}; color: {LIMA}; font-weight: 800; padding: 8px;}}"
        )
        self.tabla_ubicaciones.itemSelectionChanged.connect(self._mostrar_detalle_ubicacion_seleccionada)
        layout.addWidget(self.tabla_ubicaciones)

        grid_comp = QGridLayout()
        grid_comp.setSpacing(14)

        card_hist = QFrame()
        card_hist.setStyleSheet(
            f"QFrame {{background-color: {TARJETA}; border: 1px solid {BORDE}; border-radius: 12px;}}"
            "QLabel {border: none; background: transparent;}"
        )
        v_hist = QVBoxLayout(card_hist)
        v_hist.setContentsMargins(16, 12, 16, 12)
        self.lbl_detalle_historico = QLabel("Selecciona una ubicación para ver su último análisis.")
        self.lbl_detalle_historico.setWordWrap(True)
        self.lbl_detalle_historico.setStyleSheet(f"color: {TEXTO}; font-size: 12px;")
        v_hist.addWidget(self.lbl_detalle_historico)

        self.grafica_historica = GraficaECO2(altura_min=190)
        v_hist.addWidget(self.grafica_historica)
        grid_comp.addWidget(card_hist, 0, 0, 1, 2)

        card_diff = QFrame()
        card_diff.setStyleSheet(
            f"QFrame {{background-color: {TARJETA_ALT}; border: 1px solid {ACENTO}; border-radius: 12px;}}"
            "QLabel {border: none; background: transparent;}"
        )
        v_diff = QVBoxLayout(card_diff)
        v_diff.setContentsMargins(16, 14, 16, 14)

        lbl_diff_tit = QLabel("COMPARATIVA ACTUAL VS. UBICACIÓN")
        lbl_diff_tit.setStyleSheet(f"color: {LIMA}; font-size: 11px; font-weight: 800;")
        v_diff.addWidget(lbl_diff_tit)

        self.lbl_comparativa = QLabel("Selecciona una fila para ver diferencias.")
        self.lbl_comparativa.setWordWrap(True)
        self.lbl_comparativa.setStyleSheet(f"color: {TEXTO}; font-size: 12px;")
        v_diff.addWidget(self.lbl_comparativa)
        v_diff.addStretch()
        grid_comp.addWidget(card_diff, 0, 2)

        layout.addLayout(grid_comp, stretch=1)
        return pagina

    def _recalibrar_zona(self):
        respuesta = QMessageBox.question(
            self,
            "Recalibrar Zona",
            "Se limpiará el CSV actual para que la IA vuelva a aprender la línea base en 15 lecturas. ¿Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta == QMessageBox.StandardButton.Yes:
            os.makedirs(os.path.dirname(RUTA_CSV), exist_ok=True)
            with open(RUTA_CSV, "w", encoding="utf-8", newline="") as f:
                f.write(",".join(COLUMNAS_CSV) + "\n")
            self.grafica.mostrar_mensaje("Recalibrando... esperando nuevas lecturas.")

    def _registrar_ubicacion_actual(self):
        if not self.ultimo_diagnostico or self.ultimo_diagnostico.get("eco2") is None:
            QMessageBox.information(self, "Sin datos", "Aún no hay lecturas válidas para guardar.")
            return

        nombre_lugar = self.input_ubicacion.text().strip() or "Punto en San Miguel"
        serie_reciente = []
        if not self.ultimo_df.empty:
            serie_reciente = self.ultimo_df.tail(50)[["timestamp", "eco2"]].to_dict(orient="records")

        registro = {
            "ubicacion": nombre_lugar,
            "coordenadas": self.ubicacion_actual["coordenadas"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "temperatura": self.ultimo_diagnostico.get("temperatura"),
            "humedad": self.ultimo_diagnostico.get("humedad"),
            "presion": self.ultimo_diagnostico.get("presion"),
            "eco2": self.ultimo_diagnostico.get("eco2"),
            "tvoc": self.ultimo_diagnostico.get("tvoc"),
            "base_eco2": self.ultimo_diagnostico.get("base_eco2"),
            "limite_normal_eco2": self.ultimo_diagnostico.get("limite_normal_eco2"),
            "nivel_alerta": self.ultimo_diagnostico.get("nivel_alerta"),
            "mensaje": self.ultimo_diagnostico.get("mensaje"),
            "serie": serie_reciente,
        }

        for i, item in enumerate(self.sesiones_guardadas):
            if item.get("ubicacion", "").lower() == nombre_lugar.lower():
                self.sesiones_guardadas[i] = registro
                break
        else:
            self.sesiones_guardadas.insert(0, registro)

        self._guardar_sesiones_disco()
        self._refrescar_tabla_ubicaciones()

    def _eliminar_ubicacion_seleccionada(self):
        fila = self.tabla_ubicaciones.currentRow()
        if 0 <= fila < len(self.sesiones_guardadas):
            self.sesiones_guardadas.pop(fila)
            self._guardar_sesiones_disco()
            self._refrescar_tabla_ubicaciones()

    def _refrescar_tabla_ubicaciones(self):
        self.tabla_ubicaciones.setRowCount(len(self.sesiones_guardadas))
        for row, reg in enumerate(self.sesiones_guardadas):
            valores = [
                reg.get("ubicacion", "—"),
                reg.get("timestamp", "—"),
                f"{reg.get('temperatura', 0):.1f}",
                f"{reg.get('humedad', 0):.1f}",
                f"{reg.get('eco2', 0):.0f}",
                f"{reg.get('base_eco2', 0):.0f}",
                reg.get("nivel_alerta", "—"),
            ]
            for col, texto in enumerate(valores):
                item = QTableWidgetItem(texto)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tabla_ubicaciones.setItem(row, col, item)
        if self.sesiones_guardadas:
            self.tabla_ubicaciones.selectRow(0)

    def _mostrar_detalle_ubicacion_seleccionada(self):
        fila = self.tabla_ubicaciones.currentRow()
        if fila < 0 or fila >= len(self.sesiones_guardadas):
            return
        reg = self.sesiones_guardadas[fila]
        self.lbl_detalle_historico.setText(
            f"<b>{reg['ubicacion']}</b> ({reg['timestamp']}) · "
            f"Estado: <b>{reg['nivel_alerta']}</b> — {reg['mensaje']}<br>"
            f"Temp: {reg['temperatura']:.1f} °C · Hum: {reg['humedad']:.1f} % · "
            f"eCO2: {reg['eco2']:.0f} ppm · TVOC: {reg['tvoc']:.0f} ppb"
        )
        if reg.get("serie"):
            self.grafica_historica.actualizar(
                pd.DataFrame(reg["serie"]),
                base_eco2=float(reg.get("base_eco2", 450.0)),
                limite_normal=float(reg.get("limite_normal_eco2", 650.0)),
            )
        self._actualizar_texto_comparativa(reg)

    def _actualizar_texto_comparativa(self, reg_guardado: dict):
        if not self.ultimo_diagnostico or self.ultimo_diagnostico.get("eco2") is None:
            self.lbl_comparativa.setText("Sin lectura actual para comparar.")
            return
        actual = self.ultimo_diagnostico
        d_eco2 = actual["eco2"] - float(reg_guardado["eco2"])
        d_temp = actual["temperatura"] - float(reg_guardado["temperatura"])
        self.lbl_comparativa.setText(
            f"<b>Actual</b> vs <b>{reg_guardado['ubicacion']}</b>:<br><br>"
            f"• eCO2: {actual['eco2']:.0f} vs {reg_guardado['eco2']:.0f} ppm (<b>{d_eco2:+.0f}</b>)<br>"
            f"• Temp: {actual['temperatura']:.1f} vs {reg_guardado['temperatura']:.1f} °C (<b>{d_temp:+.1f}</b>)"
        )

    def _actualizar_panel_perfil(self):
        perfiles = self.ultimo_diagnostico.get("perfiles", {})
        if not perfiles:
            return
        perfil_activo = self.combo_perfil.currentText()
        info_activa = perfiles.get(perfil_activo, {})
        if info_activa:
            self.lbl_banner_perfil.setText(
                f"[{perfil_activo}] {info_activa['titulo']}: {info_activa['detalle']}"
            )
        for nombre_perfil, (lbl_tit, lbl_det) in self.tarjetas_sectores.items():
            datos_p = perfiles.get(nombre_perfil)
            if datos_p:
                lbl_tit.setText(datos_p["titulo"])
                lbl_det.setText(datos_p["detalle"])

    def _actualizar_datos(self):
        if not os.path.exists(RUTA_CSV):
            self.lbl_estado_flujo.setText("Estado del flujo: no existe data/datos_ambientales.csv")
            self.etiqueta_ia.setText("SIN ARCHIVO CSV")
            self.grafica.mostrar_mensaje("No se encontró data/datos_ambientales.csv")
            return

        try:
            df = pd.read_csv(RUTA_CSV)
            if df.empty:
                self.lbl_estado_flujo.setText(
                    "Estado del flujo: CSV vacío (0 filas). Verifica que COM6 esté enviando JSON."
                )
                self.etiqueta_ia.setText("ESPERANDO DATOS (0 FILAS)")
                return

            self.ultimo_df = df
            diagnostico = obtener_diagnostico_completo(ruta_csv=RUTA_CSV)
            self.ultimo_diagnostico = diagnostico
            interpretaciones = diagnostico.get("interpretaciones", {})

            ultima_fila = df.iloc[-1]
            for columna, tarjeta in self.tarjetas.items():
                if columna in ultima_fila:
                    tarjeta.actualizar(ultima_fila[columna], interpretaciones.get(columna, ""))

            self.grafica.actualizar(
                df,
                base_eco2=float(diagnostico.get("base_eco2", 450.0)),
                limite_normal=float(diagnostico.get("limite_normal_eco2", 650.0)),
            )

            nivel = diagnostico.get("nivel_alerta", "SIN_DATOS")
            mensaje = diagnostico.get("mensaje", "")
            n_muestras = diagnostico.get("muestras_analizadas", 0)
            self.lbl_estado_flujo.setText(
                f"Estado del flujo: {len(df)} filas en CSV · Ventana IA: {n_muestras} lecturas válidas"
            )
            self.etiqueta_ia.setText(f"{nivel}\n{mensaje}")

            if nivel in ("OPTIMO", "ACEPTABLE"):
                fondo_ia, texto_ia, borde_ia = "#064E3B", "#6EE7B7", ACENTO
            elif nivel in ("PRECAUCION", "CALIBRANDO"):
                fondo_ia, texto_ia, borde_ia = "#78350F", "#FDE68A", AMBAR
            elif nivel in ("CRITICO", "FALLO_HARDWARE"):
                fondo_ia, texto_ia, borde_ia = "#881337", "#FECDD3", CORAL
            else:
                fondo_ia, texto_ia, borde_ia = TARJETA_ALT, TEXTO, BORDE

            self.etiqueta_ia.setStyleSheet(
                f"background-color: {fondo_ia}; color: {texto_ia}; border: 1px solid {borde_ia}; "
                "font-size: 12px; font-weight: 800; border-radius: 10px; padding: 9px 14px;"
            )
            self._actualizar_panel_perfil()

            fila_sel = self.tabla_ubicaciones.currentRow()
            if 0 <= fila_sel < len(self.sesiones_guardadas):
                self._actualizar_texto_comparativa(self.sesiones_guardadas[fila_sel])

        except Exception as error:
            self.lbl_estado_flujo.setText(f"Error en actualización: {error}")
            self.etiqueta_ia.setText("ERROR AL LEER")
            self.grafica.mostrar_mensaje(f"Error al leer CSV/IA: {error}")


def main():
    app = QApplication(sys.argv)
    dialogo = DialogoArranque()
    if dialogo.exec() != QDialog.DialogCode.Accepted:
        return 0

    ventana = VentanaAireCentinela(dialogo.ubicacion_detectada)
    ventana.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())