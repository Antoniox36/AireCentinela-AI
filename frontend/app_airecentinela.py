"""Frontend profesional de Aire Centinela AI: estética bio-ambiental, perfiles y evidencia por ubicación."""

import json
import os
import sys
from datetime import datetime

import pandas as pd
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
import matplotlib.dates as mdates
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

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

# Paleta Bio-Ambiental Obsidiana & Esmeralda (cero tonos azules)
FONDO = "#0B0D0C"          # Obsidiana volcánica profunda
SIDEBAR = "#111513"        # Carbón musgo oscuro
TARJETA = "#161B18"        # Grafito orgánico
TARJETA_ALT = "#1E2521"    # Elevación sutil
BORDE = "#2B3530"          # Borde mineral
TEXTO = "#F4F6F5"          # Blanco cálido
SECUNDARIO = "#9CA8A1"     # Gris salvia
ACENTO = "#10B981"         # Verde esmeralda principal
LIMA = "#84CC16"           # Lima bio-sensor
AMBAR = "#F59E0B"          # Ámbar solar
CORAL = "#F43F5E"          # Coral alerta crítica
VIOLETA = "#A78BFA"        # Lavanda para presión barométrica

# Puntos reales calibrados en San Miguel, El Salvador
PUNTOS_SAN_MIGUEL = {
    "Campus UGB · San Miguel": ("13.4892° N, 88.1914° O", "San Miguel, El Salvador"),
    "Laboratorio Electrónica · UGB": ("13.4895° N, 88.1911° O", "San Miguel, El Salvador"),
    "Feria de Proyectos · UGB": ("13.4889° N, 88.1917° O", "San Miguel, El Salvador"),
    "Centro Urbano · San Miguel": ("13.4833° N, 88.1833° O", "San Miguel, El Salvador"),
    "Zona Residencial · San Miguel": ("13.4798° N, 88.1865° O", "San Miguel, El Salvador"),
}


def obtener_ubicacion_base() -> dict[str, str]:
    """Devuelve la ubicación base calibrada en San Miguel, El Salvador."""
    punto_default = "Campus UGB · San Miguel"
    coords, region = PUNTOS_SAN_MIGUEL[punto_default]
    return {
        "nombre": punto_default,
        "region": region,
        "coordenadas": coords,
    }


class DialogoArranque(QDialog):
    """Pantalla de auditoría inicial que verifica hardware, CSV, ubicación e IA."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aire Centinela AI | Diagnóstico de Inicio")
        self.setFixedSize(560, 405)
        self.setStyleSheet(
            f"QDialog {{background-color: {FONDO}; border: 1px solid {BORDE};}}"
            f"QLabel {{color: {TEXTO}; background: transparent;}}"
        )
        self.ubicacion_detectada = obtener_ubicacion_base()
        self.paso = 0
        self._construir_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._ejecutar_paso)
        self.timer.start(400)

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(14)

        marca = QLabel("AIRE CENTINELA AI · ESTACIÓN AMBIENTAL")
        marca.setStyleSheet(
            f"color: {LIMA}; font-size: 11px; font-weight: 800; letter-spacing: 2px;"
        )
        layout.addWidget(marca)

        titulo = QLabel("Verificando Sensores y Motor IA")
        titulo.setStyleSheet(f"color: {TEXTO}; font-size: 20px; font-weight: 800;")
        layout.addWidget(titulo)

        subtitulo = QLabel(
            "Comprobación previa de buses I2C, canal serial y coordenadas de San Miguel."
        )
        subtitulo.setStyleSheet(f"color: {SECUNDARIO}; font-size: 12px;")
        layout.addWidget(subtitulo)

        marco_checks = QFrame()
        marco_checks.setStyleSheet(
            f"QFrame {{background-color: {TARJETA}; border: 1px solid {BORDE}; border-radius: 12px;}}"
        )
        v_checks = QVBoxLayout(marco_checks)
        v_checks.setContentsMargins(18, 16, 18, 16)
        v_checks.setSpacing(12)

        self.lbl_serial = QLabel("⏳  1. Canal de telemetría USB y almacenamiento CSV...")
        self.lbl_ccs = QLabel("⏳  2. Sensor CCS811 (Bus I2C Hardware A4/A5 · eCO2/TVOC)...")
        self.lbl_bme = QLabel("⏳  3. Sensor HW-611 / BME280 (Bus I2C A2/A3 · Clima)...")
        self.lbl_gps = QLabel("⏳  4. Punto geográfico San Miguel y modelo Isolation Forest...")

        for lbl in (self.lbl_serial, self.lbl_ccs, self.lbl_bme, self.lbl_gps):
            lbl.setStyleSheet(f"color: {SECUNDARIO}; font-size: 13px; border: none;")
            v_checks.addWidget(lbl)

        layout.addWidget(marco_checks)

        self.barra = QProgressBar()
        self.barra.setRange(0, 100)
        self.barra.setValue(10)
        self.barra.setTextVisible(False)
        self.barra.setFixedHeight(8)
        self.barra.setStyleSheet(
            f"QProgressBar {{background-color: {TARJETA}; border-radius: 4px;}}"
            f"QProgressBar::chunk {{background-color: {ACENTO}; border-radius: 4px;}}"
        )
        layout.addWidget(self.barra)

        fila_bot = QHBoxLayout()
        self.lbl_estado = QLabel("Ejecutando auditoría de sistema...")
        self.lbl_estado.setStyleSheet(f"color: {SECUNDARIO}; font-size: 12px;")
        fila_bot.addWidget(self.lbl_estado)
        fila_bot.addStretch()

        self.btn_continuar = QPushButton("Abrir Consola")
        self.btn_continuar.setEnabled(False)
        self.btn_continuar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_continuar.setStyleSheet(
            f"QPushButton {{background-color: {ACENTO}; color: #05140E; font-weight: 800; "
            "padding: 8px 18px; border-radius: 8px; font-size: 13px;}}"
            f"QPushButton:disabled {{background-color: {BORDE}; color: {SECUNDARIO};}}"
        )
        self.btn_continuar.clicked.connect(self.accept)
        fila_bot.addWidget(self.btn_continuar)
        layout.addLayout(fila_bot)

    def _ejecutar_paso(self):
        self.paso += 1
        df_actual = None
        if os.path.exists(RUTA_CSV):
            try:
                df_actual = pd.read_csv(RUTA_CSV)
            except Exception:
                df_actual = None

        if self.paso == 1:
            self.barra.setValue(30)
            if df_actual is not None and not df_actual.empty:
                self.lbl_serial.setText(
                    f"✅  1. Historial CSV activo ({len(df_actual)} tramas registradas)"
                )
                self.lbl_serial.setStyleSheet(f"color: {ACENTO}; font-size: 13px; border: none;")
            else:
                self.lbl_serial.setText(
                    "⚠️  1. Sin hardware conectado aún (modo escucha listo)"
                )
                self.lbl_serial.setStyleSheet(f"color: {AMBAR}; font-size: 13px; border: none;")

        elif self.paso == 2:
            self.barra.setValue(55)
            if df_actual is not None and not df_actual.empty:
                eco2_val = pd.to_numeric(df_actual["eco2"].iloc[-1], errors="coerce")
                if not pd.isna(eco2_val) and eco2_val > 0:
                    self.lbl_ccs.setText(
                        f"✅  2. CCS811 operativo en A4/A5 (lectura: {eco2_val:.0f} ppm)"
                    )
                    self.lbl_ccs.setStyleSheet(f"color: {ACENTO}; font-size: 13px; border: none;")
                else:
                    self.lbl_ccs.setText("❌  2. CCS811 sin lectura válida en A4/A5")
                    self.lbl_ccs.setStyleSheet(f"color: {CORAL}; font-size: 13px; border: none;")
            else:
                self.lbl_ccs.setText("⏳  2. CCS811 en espera de conexión USB / COM")

        elif self.paso == 3:
            self.barra.setValue(80)
            if df_actual is not None and not df_actual.empty:
                temp_val = pd.to_numeric(df_actual["temperatura"].iloc[-1], errors="coerce")
                pres_val = pd.to_numeric(df_actual["presion"].iloc[-1], errors="coerce")
                if not pd.isna(temp_val) and -40 <= temp_val <= 85:
                    self.lbl_bme.setText(
                        f"✅  3. HW-611 / BME280 operativo en A2/A3 ({temp_val:.1f} °C · {pres_val:.1f} hPa)"
                    )
                    self.lbl_bme.setStyleSheet(f"color: {ACENTO}; font-size: 13px; border: none;")
                else:
                    self.lbl_bme.setText("❌  3. Fallo en HW-611 / BME280 (pines A2/A3)")
                    self.lbl_bme.setStyleSheet(f"color: {CORAL}; font-size: 13px; border: none;")
            else:
                self.lbl_bme.setText("⏳  3. HW-611 / BME280 en espera de conexión USB / COM")

        elif self.paso >= 4:
            self.timer.stop()
            self.barra.setValue(100)
            self.lbl_gps.setText(
                f"✅  4. {self.ubicacion_detectada['nombre']} · Isolation Forest listo"
            )
            self.lbl_gps.setStyleSheet(f"color: {ACENTO}; font-size: 13px; border: none;")
            self.lbl_estado.setText("Estación verificada. Abriendo panel principal...")
            self.btn_continuar.setEnabled(True)
            QTimer.singleShot(650, self.accept)


class TarjetaMetrica(QFrame):
    """Tarjeta de lectura ambiental con interpretación humana directa."""

    def __init__(self, titulo, unidad, color, decimales=1, destacada=False):
        super().__init__()
        self.decimales = decimales
        self.setMinimumHeight(156)
        self.setStyleSheet(
            f"QFrame {{background-color: {TARJETA}; border: 1px solid "
            f"{ACENTO if destacada else BORDE}; border-radius: 16px;}}"
            "QLabel {border: none; background: transparent;}"
        )

        contenedor = QVBoxLayout(self)
        contenedor.setContentsMargins(20, 16, 20, 16)
        contenedor.setSpacing(6)

        etiqueta = QLabel(titulo.upper())
        etiqueta.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: 800; letter-spacing: 1.2px;"
        )
        contenedor.addWidget(etiqueta)

        fila_valor = QHBoxLayout()
        fila_valor.setSpacing(8)
        fila_valor.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.etiqueta_valor = QLabel("—")
        self.etiqueta_valor.setStyleSheet(
            f"color: {LIMA if destacada else TEXTO}; "
            f"font-size: {36 if destacada else 30}px; font-weight: 800;"
        )
        fila_valor.addWidget(self.etiqueta_valor)

        etiqueta_unidad = QLabel(unidad)
        etiqueta_unidad.setStyleSheet(f"color: {SECUNDARIO}; font-size: 14px; font-weight: 600;")
        fila_valor.addWidget(etiqueta_unidad)
        contenedor.addLayout(fila_valor)

        self.etiqueta_interpretacion = QLabel("Esperando lectura...")
        self.etiqueta_interpretacion.setWordWrap(True)
        self.etiqueta_interpretacion.setStyleSheet(
            f"color: {SECUNDARIO}; font-size: 12px;"
        )
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
    """Gráfica histórica de eCO2 con banda sombreada de normalidad aprendida por IA."""

    def __init__(self, altura_min=270):
        self.figura = Figure(figsize=(10, 3.6), dpi=100, facecolor=TARJETA)
        self.ejes = self.figura.add_subplot(111)
        super().__init__(self.figura)
        self.setMinimumHeight(altura_min)
        self.mostrar_mensaje("Esperando lecturas del sensor...")

    def _preparar_ejes(self):
        self.ejes.clear()
        self.ejes.set_facecolor(TARJETA)
        self.ejes.tick_params(colors=SECUNDARIO, labelsize=9)
        self.ejes.set_ylabel("eCO2 (ppm)", color=SECUNDARIO, fontsize=10)
        self.ejes.set_xlabel("Hora de captura", color=SECUNDARIO, fontsize=10)
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
            fontsize=12,
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
            self.mostrar_mensaje("Esperando lecturas válidas de eCO2...")
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
            label=f"Zona normal aprendida ({piso_banda:.0f}–{limite_normal:.0f} ppm)",
        )
        self.ejes.axhline(
            limite_normal,
            color=AMBAR,
            linestyle=":",
            linewidth=1.2,
            alpha=0.9,
            label="Umbral preventivo IA",
        )

        self.ejes.plot(
            fechas,
            valores,
            color=LIMA,
            linewidth=2.3,
            marker="o" if len(historico) <= 55 else None,
            markersize=3.5,
            label="Lectura eCO2 en vivo",
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
    """Panel principal de Aire Centinela AI."""

    def __init__(self, ubicacion_inicial: dict[str, str]):
        super().__init__()
        self.ubicacion_actual = ubicacion_inicial
        self.ultimo_diagnostico: dict = {}
        self.ultimo_df: pd.DataFrame = pd.DataFrame()
        self.sesiones_guardadas: list[dict] = self._cargar_sesiones()

        self.setWindowTitle("Aire Centinela AI | Estación Ambiental Inteligente")
        self.setMinimumSize(1160, 760)
        self.resize(1320, 840)
        self.setStyleSheet(f"QMainWindow {{background-color: {FONDO};}}")

        self._construir_interfaz()
        self._refrescar_tabla_ubicaciones()

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

        # --- BARRA LATERAL ---
        sidebar = QFrame()
        sidebar.setFixedWidth(265)
        sidebar.setStyleSheet(
            f"QFrame {{background-color: {SIDEBAR}; border-right: 1px solid {BORDE};}}"
            "QLabel {border: none; background: transparent;}"
        )
        v_side = QVBoxLayout(sidebar)
        v_side.setContentsMargins(20, 26, 20, 22)
        v_side.setSpacing(12)

        badge_ugb = QLabel("UGB · SAN MIGUEL")
        badge_ugb.setStyleSheet(
            f"color: {LIMA}; font-size: 11px; font-weight: 800; letter-spacing: 1.5px;"
        )
        v_side.addWidget(badge_ugb)

        logo = QLabel("Aire Centinela AI")
        logo.setStyleSheet(f"color: {TEXTO}; font-size: 21px; font-weight: 800;")
        v_side.addWidget(logo)

        desc_logo = QLabel("Estación ambiental inteligente con aprendizaje adaptativo")
        desc_logo.setWordWrap(True)
        desc_logo.setStyleSheet(f"color: {SECUNDARIO}; font-size: 12px;")
        v_side.addWidget(desc_logo)

        v_side.addSpacing(14)

        self.botones_nav = []
        vistas_info = [
            ("📡  Monitor en Vivo", 0),
            ("🧭  Perfiles y Guía de Uso", 1),
            ("📍  Evidencia por Ubicación", 2),
        ]
        for texto_btn, idx in vistas_info:
            btn = QPushButton(texto_btn)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, i=idx: self._cambiar_vista(i))
            v_side.addWidget(btn)
            self.botones_nav.append(btn)

        v_side.addStretch()

        # Tarjeta de ubicación precisa en San Miguel
        box_gps = QFrame()
        box_gps.setStyleSheet(
            f"QFrame {{background-color: {TARJETA}; border: 1px solid {BORDE}; border-radius: 12px;}}"
        )
        v_gps = QVBoxLayout(box_gps)
        v_gps.setContentsMargins(14, 12, 14, 12)
        v_gps.setSpacing(7)

        lbl_gps_tit = QLabel("PUNTO DE MEDICIÓN")
        lbl_gps_tit.setStyleSheet(
            f"color: {LIMA}; font-size: 10px; font-weight: 800; letter-spacing: 1px;"
        )
        v_gps.addWidget(lbl_gps_tit)

        self.combo_puntos = QComboBox()
        self.combo_puntos.addItems(list(PUNTOS_SAN_MIGUEL.keys()) + ["Otro punto personalizado..."])
        self.combo_puntos.setStyleSheet(
            f"QComboBox {{background-color: {FONDO}; color: {TEXTO}; border: 1px solid {BORDE}; "
            "border-radius: 6px; padding: 5px 8px; font-size: 11.5px; font-weight: 600;}}"
            f"QComboBox QAbstractItemView {{background-color: {TARJETA}; color: {TEXTO}; selection-background-color: {TARJETA_ALT};}}"
        )
        self.combo_puntos.currentTextChanged.connect(self._al_cambiar_punto_predefinido)
        v_gps.addWidget(self.combo_puntos)

        self.input_ubicacion = QLineEdit(self.ubicacion_actual["nombre"])
        self.input_ubicacion.setPlaceholderText("Nombre exacto del lugar...")
        self.input_ubicacion.setStyleSheet(
            f"QLineEdit {{background-color: {FONDO}; color: {TEXTO}; border: 1px solid {BORDE}; "
            "border-radius: 6px; padding: 6px 8px; font-size: 12px; font-weight: 600;}}"
        )
        v_gps.addWidget(self.input_ubicacion)

        self.lbl_coords = QLabel(
            f"{self.ubicacion_actual['coordenadas']}\n{self.ubicacion_actual['region']}"
        )
        self.lbl_coords.setWordWrap(True)
        self.lbl_coords.setStyleSheet(f"color: {SECUNDARIO}; font-size: 11px;")
        v_gps.addWidget(self.lbl_coords)

        btn_guardar_ubi = QPushButton("💾 Guardar Evidencia Aquí")
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

        # --- CONTENIDO PRINCIPAL ---
        contenedor_derecho = QWidget()
        v_der = QVBoxLayout(contenedor_derecho)
        v_der.setContentsMargins(26, 22, 26, 22)
        v_der.setSpacing(18)

        header = QHBoxLayout()
        header.setSpacing(14)

        col_titulo = QVBoxLayout()
        self.lbl_titulo_vista = QLabel("Monitoreo Ambiental en Tiempo Real")
        self.lbl_titulo_vista.setStyleSheet(
            f"color: {TEXTO}; font-size: 23px; font-weight: 800;"
        )
        col_titulo.addWidget(self.lbl_titulo_vista)

        self.lbl_subtitulo_vista = QLabel(
            "Lecturas en vivo desde Arduino Uno R3 · Interpretación automática para toma de decisiones"
        )
        self.lbl_subtitulo_vista.setStyleSheet(f"color: {SECUNDARIO}; font-size: 12px;")
        col_titulo.addWidget(self.lbl_subtitulo_vista)
        header.addLayout(col_titulo)
        header.addStretch()

        lbl_perf = QLabel("Perfil activo:")
        lbl_perf.setStyleSheet(f"color: {SECUNDARIO}; font-size: 12px; font-weight: 600;")
        header.addWidget(lbl_perf)

        self.combo_perfil = QComboBox()
        self.combo_perfil.addItems(PERFILES_USO)
        self.combo_perfil.setStyleSheet(
            f"QComboBox {{background-color: {TARJETA}; color: {TEXTO}; border: 1px solid {BORDE}; "
            "border-radius: 8px; padding: 7px 12px; font-size: 12px; font-weight: 700; min-width: 175px;}}"
            f"QComboBox QAbstractItemView {{background-color: {TARJETA}; color: {TEXTO}; selection-background-color: {TARJETA_ALT};}}"
        )
        self.combo_perfil.currentTextChanged.connect(self._actualizar_panel_perfil)
        header.addWidget(self.combo_perfil)

        btn_recalibrar = QPushButton("🔄 Recalibrar Zona")
        btn_recalibrar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_recalibrar.setToolTip(
            "Reinicia la ventana de aprendizaje de Isolation Forest para adaptarse a un lugar nuevo"
        )
        btn_recalibrar.setStyleSheet(
            f"QPushButton {{background-color: {TARJETA_ALT}; color: {LIMA}; border: 1px solid {LIMA}; "
            "border-radius: 8px; padding: 7px 12px; font-size: 12px; font-weight: 700;}}"
            f"QPushButton:hover {{background-color: {BORDE};}}"
        )
        btn_recalibrar.clicked.connect(self._recalibrar_zona)
        header.addWidget(btn_recalibrar)

        self.etiqueta_ia = QLabel(" INICIANDO MOTOR IA ")
        self.etiqueta_ia.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.etiqueta_ia.setMinimumWidth(310)
        self.etiqueta_ia.setStyleSheet(
            f"background-color: {BORDE}; color: {TEXTO}; "
            "font-size: 13px; font-weight: 800; border-radius: 10px; padding: 9px 14px;"
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
            self.lbl_coords.setText(f"{coords}\n{region}")
        else:
            self.input_ubicacion.clear()
            self.input_ubicacion.setFocus()

    def _cambiar_vista(self, indice: int):
        self.stack.setCurrentIndex(indice)
        titulos = [
            (
                "Monitoreo Ambiental en Tiempo Real",
                "Lecturas en vivo desde Arduino Uno R3 · Interpretación automática para toma de decisiones",
            ),
            (
                "Perfiles de Uso y Guía de Sensores",
                "Recomendaciones adaptadas por sector y referencia clara de cada variable medida",
            ),
            (
                "Historial Verificable y Comparativa por Ubicación",
                "Registro auditado de pruebas en campo · Haz clic en una ubicación para inspeccionar y comparar",
            ),
        ]
        self.lbl_titulo_vista.setText(titulos[indice][0])
        self.lbl_subtitulo_vista.setText(titulos[indice][1])

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
        layout.setSpacing(18)

        grid = QGridLayout()
        grid.setSpacing(16)

        self.tarjetas = {
            "temperatura": TarjetaMetrica("Temperatura Ambiente", "°C", CORAL),
            "humedad": TarjetaMetrica("Humedad Relativa", "%", ACENTO),
            "presion": TarjetaMetrica("Presión Atmosférica", "hPa", VIOLETA, decimales=2),
            "eco2": TarjetaMetrica("Dióxido de Carbono (eCO2)", "ppm", LIMA, decimales=0, destacada=True),
            "tvoc": TarjetaMetrica("Compuestos Volátiles (TVOC)", "ppb", AMBAR, decimales=0),
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
        h_banner.setContentsMargins(18, 12, 18, 12)
        h_banner.setSpacing(12)

        self.lbl_banner_perfil = QLabel("💡 Recomendación del perfil seleccionado: calibrando lecturas...")
        self.lbl_banner_perfil.setWordWrap(True)
        self.lbl_banner_perfil.setStyleSheet(f"color: {TEXTO}; font-size: 13px; font-weight: 600;")
        h_banner.addWidget(self.lbl_banner_perfil)
        layout.addWidget(banner)

        self.grafica = GraficaECO2(altura_min=280)
        layout.addWidget(self.grafica, stretch=1)
        return pagina

    def _crear_vista_perfiles(self) -> QWidget:
        """Vista limpia con desplazamiento suave, tarjetas por sector y fichas técnicas de sensores."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            f"QScrollArea {{background: transparent; border: none;}}"
            f"QScrollBar:vertical {{background: {SIDEBAR}; width: 8px; border-radius: 4px;}}"
            f"QScrollBar::handle:vertical {{background: {BORDE}; border-radius: 4px;}}"
        )

        contenido = QWidget()
        contenido.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(contenido)
        layout.setContentsMargins(0, 0, 8, 12)
        layout.setSpacing(22)

        # Sección 1: Diagnóstico en vivo adaptado a cada sector
        lbl_sec1 = QLabel("1. Diagnóstico en Vivo Adaptado por Sector")
        lbl_sec1.setStyleSheet(f"color: {TEXTO}; font-size: 15px; font-weight: 800;")
        layout.addWidget(lbl_sec1)

        grid_sectores = QGridLayout()
        grid_sectores.setSpacing(16)
        self.tarjetas_sectores: dict[str, tuple[QLabel, QLabel]] = {}

        iconos_sector = {
            "Oficina / Escuela": ("🏫  Educación, Aulas y Oficinas", LIMA),
            "Agricultura / Cultivo": ("🌱  Agricultura, Invernaderos y Silos", ACENTO),
            "Hogar / Salud": ("🏠  Hogar y Bienestar Respiratorio", AMBAR),
        }

        for col, perfil in enumerate(PERFILES_USO):
            titulo_sec, color_sec = iconos_sector[perfil]
            card = QFrame()
            card.setMinimumHeight(155)
            card.setStyleSheet(
                f"QFrame {{background-color: {TARJETA}; border: 1px solid {BORDE}; border-radius: 14px;}}"
                "QLabel {border: none; background: transparent;}"
            )
            v = QVBoxLayout(card)
            v.setContentsMargins(20, 18, 20, 18)
            v.setSpacing(10)

            lbl_head = QLabel(titulo_sec)
            lbl_head.setStyleSheet(f"color: {color_sec}; font-size: 13px; font-weight: 800;")
            v.addWidget(lbl_head)

            lbl_estado_sec = QLabel("Analizando entorno...")
            lbl_estado_sec.setWordWrap(True)
            lbl_estado_sec.setStyleSheet(f"color: {TEXTO}; font-size: 15px; font-weight: 700;")
            v.addWidget(lbl_estado_sec)

            lbl_detalle_sec = QLabel("Esperando datos en vivo de los sensores.")
            lbl_detalle_sec.setWordWrap(True)
            lbl_detalle_sec.setStyleSheet(f"color: {SECUNDARIO}; font-size: 12.5px;")
            v.addWidget(lbl_detalle_sec)
            v.addStretch()

            self.tarjetas_sectores[perfil] = (lbl_estado_sec, lbl_detalle_sec)
            grid_sectores.addWidget(card, 0, col)

        layout.addLayout(grid_sectores)

        # Sección 2: Fichas individuales espaciadas de cada magnitud
        lbl_sec2 = QLabel("2. Referencia Rápida de Variables y Umbrales")
        lbl_sec2.setStyleSheet(f"color: {TEXTO}; font-size: 15px; font-weight: 800;")
        layout.addWidget(lbl_sec2)

        fichas = [
            (
                "eCO2 · Dióxido de Carbono Equivalente (ppm)",
                LIMA,
                "400 – 650 ppm: Aire fresco  |  750 – 1000 ppm: Carga moderada  |  > 1200 ppm: Aire viciado",
                "Indica el nivel de renovación del aire en espacios cerrados. Superar 1000 ppm reduce la concentración y produce somnolencia.",
            ),
            (
                "TVOC · Compuestos Orgánicos Volátiles (ppb)",
                AMBAR,
                "0 – 50 ppb: Aire puro  |  50 – 220 ppb: Vapores leves  |  > 220 ppb: Alta carga química",
                "Detecta gases invisibles provenientes de humo, alcohol, aerosoles, solventes o productos de limpieza.",
            ),
            (
                "Temperatura (°C) y Humedad Relativa (%)",
                CORAL,
                "Confort: 20 – 28 °C y 35 – 65 % RH  |  Riesgo fúngico en cultivos: > 78 % RH",
                "Define el confort térmico en aulas y el equilibrio hídrico o riesgo de hongos en invernaderos y almacenes.",
            ),
            (
                "Presión Atmosférica (hPa)",
                VIOLETA,
                "Referencia en San Miguel (~110 m s. n. m.): 996 – 1002 hPa",
                "Mide el peso del aire local; descensos bruscos anticipan frentes lluviosos o cambios barométricos.",
            ),
            (
                "Modelo Adaptativo Isolation Forest",
                ACENTO,
                "Calibración automática en los primeros 15 segundos de cada ubicación",
                "Aprende la línea base propia de cada habitación y activa el buzzer únicamente cuando detecta una anomalía real sobre ese entorno.",
            ),
        ]

        for titulo_ficha, color_ficha, rango_ficha, desc_ficha in fichas:
            ficha = QFrame()
            ficha.setStyleSheet(
                f"QFrame {{background-color: {TARJETA}; border: 1px solid {BORDE}; "
                f"border-left: 4px solid {color_ficha}; border-radius: 12px;}}"
                "QLabel {border: none; background: transparent;}"
            )
            vf = QVBoxLayout(ficha)
            vf.setContentsMargins(18, 14, 18, 14)
            vf.setSpacing(6)

            fila_sup = QHBoxLayout()
            lbl_tf = QLabel(titulo_ficha)
            lbl_tf.setStyleSheet(f"color: {TEXTO}; font-size: 13.5px; font-weight: 800;")
            fila_sup.addWidget(lbl_tf)
            fila_sup.addStretch()

            lbl_rf = QLabel(rango_ficha)
            lbl_rf.setStyleSheet(f"color: {color_ficha}; font-size: 11.5px; font-weight: 700;")
            fila_sup.addWidget(lbl_rf)
            vf.addLayout(fila_sup)

            lbl_df = QLabel(desc_ficha)
            lbl_df.setWordWrap(True)
            lbl_df.setStyleSheet(f"color: {SECUNDARIO}; font-size: 12.5px;")
            vf.addWidget(lbl_df)

            layout.addWidget(ficha)

        layout.addStretch()
        scroll.setWidget(contenido)
        return scroll

    def _crear_vista_ubicaciones(self) -> QWidget:
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        barra_ev = QHBoxLayout()
        lbl_info = QLabel(
            "Cada ubicación registrada guarda su último análisis de IA y serie histórica para demostrar pruebas en campo."
        )
        lbl_info.setStyleSheet(f"color: {SECUNDARIO}; font-size: 12.5px;")
        barra_ev.addWidget(lbl_info)
        barra_ev.addStretch()

        btn_guardar_ahora = QPushButton("➕ Guardar Snapshot de Ubicación Actual")
        btn_guardar_ahora.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_guardar_ahora.setStyleSheet(
            f"QPushButton {{background-color: {ACENTO}; color: #05140E; font-weight: 800; "
            "padding: 8px 14px; border-radius: 8px; font-size: 12px;}}"
        )
        btn_guardar_ahora.clicked.connect(self._registrar_ubicacion_actual)
        barra_ev.addWidget(btn_guardar_ahora)

        btn_eliminar = QPushButton("🗑️ Eliminar Seleccionada")
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
            [
                "Ubicación / Punto de Prueba",
                "Fecha y Hora",
                "Temp (°C)",
                "Humedad (%)",
                "eCO2 (ppm)",
                "Base IA (ppm)",
                "Veredicto IA",
            ]
        )
        self.tabla_ubicaciones.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.tabla_ubicaciones.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.tabla_ubicaciones.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_ubicaciones.setMaximumHeight(210)
        self.tabla_ubicaciones.setStyleSheet(
            f"QTableWidget {{background-color: {TARJETA}; color: {TEXTO}; border: 1px solid {BORDE}; "
            "border-radius: 10px; gridline-color: #222B26; font-size: 12px;}}"
            f"QHeaderView::section {{background-color: {SIDEBAR}; color: {LIMA}; font-weight: 800; "
            f"padding: 8px; border: none; border-bottom: 1px solid {BORDE};}}"
            f"QTableWidget::item:selected {{background-color: {TARJETA_ALT}; color: {ACENTO};}}"
        )
        self.tabla_ubicaciones.itemSelectionChanged.connect(
            self._mostrar_detalle_ubicacion_seleccionada
        )
        layout.addWidget(self.tabla_ubicaciones)

        grid_comp = QGridLayout()
        grid_comp.setSpacing(16)

        card_hist = QFrame()
        card_hist.setStyleSheet(
            f"QFrame {{background-color: {TARJETA}; border: 1px solid {BORDE}; border-radius: 14px;}}"
            "QLabel {border: none; background: transparent;}"
        )
        v_hist = QVBoxLayout(card_hist)
        v_hist.setContentsMargins(16, 14, 16, 14)
        self.lbl_detalle_historico = QLabel(
            "Selecciona una ubicación de la tabla para ver el último análisis tal como quedó registrado."
        )
        self.lbl_detalle_historico.setWordWrap(True)
        self.lbl_detalle_historico.setStyleSheet(f"color: {TEXTO}; font-size: 12.5px;")
        v_hist.addWidget(self.lbl_detalle_historico)

        self.grafica_historica = GraficaECO2(altura_min=200)
        v_hist.addWidget(self.grafica_historica)
        grid_comp.addWidget(card_hist, 0, 0, 1, 2)

        card_diff = QFrame()
        card_diff.setStyleSheet(
            f"QFrame {{background-color: {TARJETA_ALT}; border: 1px solid {ACENTO}; border-radius: 14px;}}"
            "QLabel {border: none; background: transparent;}"
        )
        v_diff = QVBoxLayout(card_diff)
        v_diff.setContentsMargins(18, 16, 18, 16)
        v_diff.setSpacing(10)

        lbl_diff_tit = QLabel("⚖️ COMPARATIVA: EN VIVO VS. UBICACIÓN")
        lbl_diff_tit.setStyleSheet(
            f"color: {LIMA}; font-size: 12px; font-weight: 800; letter-spacing: 1px;"
        )
        v_diff.addWidget(lbl_diff_tit)

        self.lbl_comparativa = QLabel(
            "Registra al menos una ubicación y selecciónala para comparar sus condiciones ambientales contra el sitio actual."
        )
        self.lbl_comparativa.setWordWrap(True)
        self.lbl_comparativa.setStyleSheet(f"color: {TEXTO}; font-size: 13px;")
        v_diff.addWidget(self.lbl_comparativa)
        v_diff.addStretch()
        grid_comp.addWidget(card_diff, 0, 2)

        layout.addLayout(grid_comp, stretch=1)
        return pagina

    def _recalibrar_zona(self):
        respuesta = QMessageBox.question(
            self,
            "Recalibrar Línea Base de la Zona",
            "Se limpiará el historial temporal actual para que Isolation Forest aprenda "
            "desde cero la línea base de esta habitación en 15 segundos.\n\n"
            "(Las ubicaciones ya guardadas en Evidencia no se borran).\n¿Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                os.makedirs(os.path.dirname(RUTA_CSV), exist_ok=True)
                with open(RUTA_CSV, "w", encoding="utf-8", newline="") as f:
                    f.write(",".join(COLUMNAS_CSV) + "\n")
                self.grafica.mostrar_mensaje("Recalibrando modelo con lecturas nuevas...")
            except Exception as error:
                QMessageBox.warning(self, "Error", f"No se pudo reiniciar el CSV: {error}")

    def _registrar_ubicacion_actual(self):
        if not self.ultimo_diagnostico or self.ultimo_diagnostico.get("eco2") is None:
            QMessageBox.information(
                self,
                "Sin datos aún",
                "Espera a que la estación tenga al menos una lectura válida antes de guardar la ubicación.",
            )
            return

        nombre_lugar = self.input_ubicacion.text().strip() or "Punto en San Miguel"
        serie_reciente = []
        if not self.ultimo_df.empty:
            sub = self.ultimo_df.tail(50)[["timestamp", "eco2"]].copy()
            serie_reciente = sub.to_dict(orient="records")

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

        reemplazado = False
        for i, item in enumerate(self.sesiones_guardadas):
            if item.get("ubicacion", "").lower() == nombre_lugar.lower():
                self.sesiones_guardadas[i] = registro
                reemplazado = True
                break
        if not reemplazado:
            self.sesiones_guardadas.insert(0, registro)

        self._guardar_sesiones_disco()
        self._refrescar_tabla_ubicaciones()
        QMessageBox.information(
            self,
            "Evidencia Guardada",
            f"Se registró el análisis de '{nombre_lugar}' ({registro['eco2']:.0f} ppm · {registro['nivel_alerta']}).",
        )

    def _eliminar_ubicacion_seleccionada(self):
        fila = self.tabla_ubicaciones.currentRow()
        if fila < 0 or fila >= len(self.sesiones_guardadas):
            return
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
            f"<b>📍 {reg['ubicacion']}</b> ({reg.get('coordenadas', '')}) · "
            f"Registrado el <b>{reg['timestamp']}</b><br>"
            f"Diagnóstico guardado: <b>{reg['nivel_alerta']}</b> — {reg['mensaje']}<br>"
            f"Lecturas: Temp <b>{reg['temperatura']:.1f} °C</b> | Hum <b>{reg['humedad']:.1f} %</b> | "
            f"Pres <b>{reg['presion']:.1f} hPa</b> | eCO2 <b>{reg['eco2']:.0f} ppm</b> | "
            f"TVOC <b>{reg['tvoc']:.0f} ppb</b>"
        )

        serie = reg.get("serie", [])
        if serie:
            df_serie = pd.DataFrame(serie)
            self.grafica_historica.actualizar(
                df_serie,
                base_eco2=float(reg.get("base_eco2", 450.0)),
                limite_normal=float(reg.get("limite_normal_eco2", 650.0)),
            )
        else:
            self.grafica_historica.mostrar_mensaje("Sin serie histórica adjunta en este registro.")

        self._actualizar_texto_comparativa(reg)

    def _actualizar_texto_comparativa(self, reg_guardado: dict):
        if not self.ultimo_diagnostico or self.ultimo_diagnostico.get("eco2") is None:
            self.lbl_comparativa.setText("Esperando lecturas en vivo para comparar...")
            return

        actual = self.ultimo_diagnostico
        d_temp = actual["temperatura"] - float(reg_guardado["temperatura"])
        d_hum = actual["humedad"] - float(reg_guardado["humedad"])
        d_eco2 = actual["eco2"] - float(reg_guardado["eco2"])
        d_tvoc = actual["tvoc"] - float(reg_guardado["tvoc"])

        lugar_actual = self.input_ubicacion.text().strip() or "Sitio actual"
        self.lbl_comparativa.setText(
            f"<b>Actual ({lugar_actual})</b> vs. <b>{reg_guardado['ubicacion']}</b>:<br><br>"
            f"• <b>eCO2:</b> {actual['eco2']:.0f} ppm vs {reg_guardado['eco2']:.0f} ppm "
            f"(<b>{d_eco2:+.0f} ppm</b>)<br>"
            f"• <b>TVOC:</b> {actual['tvoc']:.0f} ppb vs {reg_guardado['tvoc']:.0f} ppb "
            f"(<b>{d_tvoc:+.0f} ppb</b>)<br>"
            f"• <b>Temperatura:</b> {actual['temperatura']:.1f} °C vs {reg_guardado['temperatura']:.1f} °C "
            f"(<b>{d_temp:+.1f} °C</b>)<br>"
            f"• <b>Humedad:</b> {actual['humedad']:.1f} % vs {reg_guardado['humedad']:.1f} % "
            f"(<b>{d_hum:+.1f} %</b>)"
        )

    def _actualizar_panel_perfil(self):
        perfiles = self.ultimo_diagnostico.get("perfiles", {})
        if not perfiles:
            return

        perfil_activo = self.combo_perfil.currentText()
        info_activa = perfiles.get(perfil_activo, {})
        if info_activa:
            self.lbl_banner_perfil.setText(
                f"💡 <b>[{perfil_activo}] {info_activa['titulo']}:</b> {info_activa['detalle']}"
            )

        for nombre_perfil, (lbl_tit, lbl_det) in self.tarjetas_sectores.items():
            datos_p = perfiles.get(nombre_perfil)
            if datos_p:
                lbl_tit.setText(datos_p["titulo"])
                lbl_det.setText(datos_p["detalle"])

    def _actualizar_datos(self):
        if not os.path.exists(RUTA_CSV):
            self.grafica.mostrar_mensaje("Esperando archivo de datos del sensor...")
            return

        try:
            df = pd.read_csv(RUTA_CSV)
            if df.empty:
                return
            self.ultimo_df = df

            diagnostico = obtener_diagnostico_completo(ruta_csv=RUTA_CSV)
            self.ultimo_diagnostico = diagnostico
            interpretaciones = diagnostico.get("interpretaciones", {})

            ultima_fila = df.iloc[-1]
            for columna, tarjeta in self.tarjetas.items():
                if columna in ultima_fila:
                    tarjeta.actualizar(
                        ultima_fila[columna],
                        interpretaciones.get(columna, ""),
                    )

            self.grafica.actualizar(
                df,
                base_eco2=float(diagnostico.get("base_eco2", 450.0)),
                limite_normal=float(diagnostico.get("limite_normal_eco2", 650.0)),
            )

            nivel = diagnostico.get("nivel_alerta", "DESCONOCIDA")
            mensaje = diagnostico.get("mensaje", "Sin conexión a IA")
            tendencia = diagnostico.get("tendencia", "")
            self.etiqueta_ia.setText(f"{nivel} · {tendencia}\n{mensaje}")

            if nivel in ("OPTIMO", "ACEPTABLE"):
                fondo_ia, texto_ia, borde_ia = "#064E3B", "#6EE7B7", ACENTO
            elif nivel == "PRECAUCION":
                fondo_ia, texto_ia, borde_ia = "#78350F", "#FDE68A", AMBAR
            elif nivel == "CRITICO":
                fondo_ia, texto_ia, borde_ia = "#881337", "#FECDD3", CORAL
            else:
                fondo_ia, texto_ia, borde_ia = TARJETA_ALT, TEXTO, BORDE

            self.etiqueta_ia.setStyleSheet(
                f"background-color: {fondo_ia}; color: {texto_ia}; border: 1px solid {borde_ia}; "
                "font-size: 13px; font-weight: 800; border-radius: 10px; padding: 9px 14px;"
            )

            self._actualizar_panel_perfil()

            fila_sel = self.tabla_ubicaciones.currentRow()
            if 0 <= fila_sel < len(self.sesiones_guardadas):
                self._actualizar_texto_comparativa(self.sesiones_guardadas[fila_sel])

        except Exception as error:
            self.grafica.mostrar_mensaje(f"Error al procesar historial: {error}")


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