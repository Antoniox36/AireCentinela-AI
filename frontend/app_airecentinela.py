"""Frontend de AireCentinela AI: monitoreo ambiental e integración con IA."""

import sys
import os
import pandas as pd

# Asegurar que reconozca el directorio raíz para importar el motor_ia.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ia_engine.motor_ia import obtener_diagnostico_completo

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates

RUTA_CSV = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'data', 'datos_ambientales.csv')
)
COLUMNAS_CSV = ('timestamp', 'temperatura', 'humedad', 'presion', 'eco2', 'tvoc')
INTERVALO_ACTUALIZACION_MS = 3000

FONDO = '#0B1220'
TARJETA = '#151F30'
BORDE = '#2A3850'
TEXTO = '#F1F5F9'
SECUNDARIO = '#9DAFC3'
CIAN = '#50D7FF'


class TarjetaMetrica(QFrame):
    """Tarjeta reutilizable para presentar una lectura ambiental."""

    def __init__(self, titulo, unidad, color, decimales=1, destacada=False):
        super().__init__()
        self.decimales = decimales
        self.setMinimumHeight(143)
        self.setStyleSheet(
            f"QFrame {{background-color: {TARJETA}; border: 1px solid "
            f"{CIAN if destacada else BORDE}; border-radius: 15px;}}"
            "QLabel {border: none; background: transparent;}"
        )

        contenedor = QVBoxLayout(self)
        contenedor.setContentsMargins(19, 17, 19, 17)
        contenedor.setSpacing(6)

        etiqueta = QLabel(titulo.upper())
        etiqueta.setStyleSheet(
            f'color: {color}; '
            'font-size: 12px; font-weight: 700; letter-spacing: 1px;'
        )
        contenedor.addWidget(etiqueta)

        fila_valor = QHBoxLayout()
        fila_valor.setSpacing(8)
        fila_valor.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.etiqueta_valor = QLabel('—')
        self.etiqueta_valor.setStyleSheet(
            f'color: {CIAN if destacada else TEXTO}; '
            f'font-size: {34 if destacada else 29}px; font-weight: 800;'
        )
        fila_valor.addWidget(self.etiqueta_valor)

        etiqueta_unidad = QLabel(unidad)
        etiqueta_unidad.setStyleSheet(f'color: {SECUNDARIO}; font-size: 14px;')
        fila_valor.addWidget(etiqueta_unidad)
        contenedor.addLayout(fila_valor)
        contenedor.addStretch()

    def actualizar(self, valor):
        """Convierte lecturas inválidas en un guion sin romper la interfaz."""
        numero = pd.to_numeric(valor, errors='coerce')
        if pd.isna(numero):
            self.etiqueta_valor.setText('—')
        else:
            self.etiqueta_valor.setText(f'{float(numero):.{self.decimales}f}')


class GraficaECO2(FigureCanvasQTAgg):
    """Gráfica histórica de eCO2 integrada con Matplotlib en Qt."""

    def __init__(self):
        self.figura = Figure(figsize=(10, 4), dpi=100, facecolor=TARJETA)
        self.ejes = self.figura.add_subplot(111)
        super().__init__(self.figura)
        self.setMinimumHeight(300)
        self.mostrar_mensaje('Esperando lecturas del sensor...')

    def _preparar_ejes(self):
        self.ejes.clear()
        self.ejes.set_facecolor(TARJETA)
        self.ejes.tick_params(colors=SECUNDARIO, labelsize=9)
        self.ejes.set_ylabel('eCO2 (ppm)', color=SECUNDARIO, fontsize=10)
        self.ejes.set_xlabel('Fecha y hora', color=SECUNDARIO, fontsize=10)
        self.ejes.grid(True, color=BORDE, linestyle='--', linewidth=0.7, alpha=0.8)
        self.ejes.set_axisbelow(True)
        for borde in self.ejes.spines.values():
            borde.set_color(BORDE)

    def mostrar_mensaje(self, mensaje):
        self._preparar_ejes()
        self.ejes.text(
            0.5, 0.5, mensaje,
            transform=self.ejes.transAxes,
            ha='center', va='center', color=SECUNDARIO, fontsize=12,
        )
        self.figura.tight_layout(pad=2)
        self.draw_idle()

    def actualizar(self, datos_csv):
        historico = pd.DataFrame({
            'fecha': pd.to_datetime(datos_csv['timestamp'], errors='coerce'),
            'eco2': pd.to_numeric(datos_csv['eco2'], errors='coerce'),
        }).dropna().sort_values('fecha')

        if historico.empty:
            self.mostrar_mensaje('No hay lecturas válidas para graficar.')
            return

        self._preparar_ejes()
        self.ejes.plot(
            historico['fecha'].tolist(),
            historico['eco2'].to_numpy(),
            color=CIAN,
            linewidth=2.2,
            marker='o' if len(historico) <= 40 else None,
            markersize=3.5,
        )
        localizador = mdates.AutoDateLocator(minticks=3, maxticks=8)
        self.ejes.xaxis.set_major_locator(localizador)
        self.ejes.xaxis.set_major_formatter(mdates.ConciseDateFormatter(localizador))
        self.ejes.margins(x=0.03, y=0.18)
        self.figura.tight_layout(pad=2)
        self.draw_idle()


class VentanaAireCentinela(QMainWindow):
    """Panel principal, encargado de coordinar el CSV y el motor de IA."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle('AireCentinela AI | Monitoreo ambiental')
        self.setMinimumSize(1050, 725)
        self.resize(1250, 820)
        self.setStyleSheet(f'QMainWindow {{background-color: {FONDO};}}')
        self._construir_interfaz()

    def _construir_interfaz(self):
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        layout_principal = QVBoxLayout(widget_central)
        layout_principal.setContentsMargins(30, 30, 30, 30)
        layout_principal.setSpacing(25)

        # 1. Panel Superior y Semáforo de IA
        panel_superior = QHBoxLayout()
        titulo = QLabel('Monitoreo en Tiempo Real')
        titulo.setStyleSheet(f'color: {TEXTO}; font-size: 26px; font-weight: 800;')
        panel_superior.addWidget(titulo)
        panel_superior.addStretch()

        self.etiqueta_ia = QLabel(' INICIANDO MOTOR IA ')
        self.etiqueta_ia.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.etiqueta_ia.setMinimumWidth(300)
        self.etiqueta_ia.setStyleSheet(
            f'background-color: {BORDE}; color: {TEXTO}; '
            'font-size: 14px; font-weight: bold; border-radius: 10px; padding: 10px;'
        )
        panel_superior.addWidget(self.etiqueta_ia)
        layout_principal.addLayout(panel_superior)

        # 2. Panel de Tarjetas de Métricas
        grid_metricas = QGridLayout()
        grid_metricas.setSpacing(20)

        self.tarjetas = {
            'temperatura': TarjetaMetrica('Temperatura', '°C', '#FF6B6B'),
            'humedad': TarjetaMetrica('Humedad', '%', '#48BB78'),
            'presion': TarjetaMetrica('Presión', 'hPa', '#A0AEC0', decimales=2),
            'eco2': TarjetaMetrica('eCO2 (Gas)', 'ppm', CIAN, decimales=0, destacada=True),
            'tvoc': TarjetaMetrica('TVOC', 'ppb', '#ED8936', decimales=0)
        }

        grid_metricas.addWidget(self.tarjetas['temperatura'], 0, 0)
        grid_metricas.addWidget(self.tarjetas['humedad'], 0, 1)
        grid_metricas.addWidget(self.tarjetas['presion'], 0, 2)
        grid_metricas.addWidget(self.tarjetas['eco2'], 1, 0, 1, 2)
        grid_metricas.addWidget(self.tarjetas['tvoc'], 1, 2)

        layout_principal.addLayout(grid_metricas)

        # 3. Lienzo de Gráfica Histórica
        self.grafica = GraficaECO2()
        layout_principal.addWidget(self.grafica, stretch=1)

        # 4. Hilo de Actualización
        self.temporizador = QTimer(self)
        self.temporizador.timeout.connect(self._actualizar_datos)
        self.temporizador.start(INTERVALO_ACTUALIZACION_MS)

    def _actualizar_datos(self):
        if not os.path.exists(RUTA_CSV):
            self.grafica.mostrar_mensaje('Esperando datos del sensor...')
            return

        try:
            df = pd.read_csv(RUTA_CSV)
            if df.empty:
                return

            # Actualizar tarjetas visuales
            ultima_fila = df.iloc[-1]
            for columna, tarjeta in self.tarjetas.items():
                if columna in ultima_fila:
                    tarjeta.actualizar(ultima_fila[columna])

            # Actualizar gráfica
            self.grafica.actualizar(df)

            # Integración con IA de Samuel
            diagnostico = obtener_diagnostico_completo(ruta_csv=RUTA_CSV)
            nivel = diagnostico.get('nivel_alerta', 'DESCONOCIDA')
            mensaje = diagnostico.get('mensaje', 'Sin conexión a IA')
            tendencia = diagnostico.get('tendencia', '')

            texto_mostrar = f"{nivel} | {tendencia}\n{mensaje}"

            # Control de colores del semáforo IA
            if nivel in ['OPTIMO', 'ACEPTABLE']:
                fondo_ia, texto_ia = '#22543D', '#9AE6B4' # Verde
            elif nivel == 'PRECAUCION':
                fondo_ia, texto_ia = '#744210', '#FBD38D' # Amarillo
            elif nivel == 'CRITICO':
                fondo_ia, texto_ia = '#742A2A', '#FEB2B2' # Rojo
            else:
                fondo_ia, texto_ia = BORDE, TEXTO         # Gris

            self.etiqueta_ia.setText(texto_mostrar)
            self.etiqueta_ia.setStyleSheet(
                f'background-color: {fondo_ia}; color: {texto_ia}; '
                'font-size: 14px; font-weight: bold; border-radius: 10px; padding: 10px;'
            )

        except Exception as e:
            self.grafica.mostrar_mensaje(f'Error al leer historial: {str(e)}')


def main():
    app = QApplication(sys.argv)
    ventana = VentanaAireCentinela()
    ventana.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()