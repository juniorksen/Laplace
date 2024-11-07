from flask import render_template, request, Blueprint, redirect, url_for
import matplotlib.pyplot as plt
import numpy as np
import os
from scipy.integrate import quad
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.animation import FuncAnimation
from osgeo import gdal

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/calcular_caudal', methods=['POST'])
def calcular_caudal():
    # Recoge los parámetros de entrada del formulario
    fecha = request.form.get('fecha')
    intensidad = float(request.form.get('intensidad', 0))
    duracion = float(request.form.get('duracion', 0))
    ancho = float(request.form.get('ancho', 0))
    profundidad = float(request.form.get('profundidad', 0))
    pendiente = float(request.form.get('pendiente', 0))

    # Constantes para el cálculo
    K = 1.2
    tau = 3.5
    absorcion = 0.5
    drenaje = 0.4

    caudal = calcular_caudal_laplace(intensidad, duracion, ancho, profundidad, pendiente, K, tau, absorcion, drenaje)
    graph_path = generar_grafico(intensidad, caudal, duracion)
    sim_path = generar_simulacion_inundacion_video("C:/Users/alfon/arangod/DEM.tif", caudal)
    dem_path = generar_dem_solo("C:/Users/alfon/arangod/DEM.tif")
    anim_path = generar_animacion_inundacion("C:/Users/alfon/arangod/DEM.tif", caudal)

    return redirect(url_for('main.resultado', fecha=fecha, caudal=caudal, graph_path=graph_path,
                            sim_path=sim_path, dem_path=dem_path, anim_path=anim_path, absorcion=absorcion, drenaje=drenaje))

def calcular_caudal_laplace(intensidad, duracion, ancho, profundidad, pendiente, K, tau, absorcion, drenaje):
    def f_t(t):
        return K * intensidad * np.exp(-absorcion * t) * (ancho * profundidad * pendiente) / (1 + drenaje * t)

    s = 1 / tau
    integral, _ = quad(lambda t: f_t(t) * np.exp(-s * t), 0, duracion)
    return integral

def generar_grafico(intensidad, caudal, duracion):
    plt.figure()
    t = np.linspace(0, duracion, 100)
    caudal_values = intensidad * np.exp(-t / duracion) * caudal  # Ejemplo de datos de caudal

    plt.plot(t, caudal_values, label='Caudal (m³/s)')
    plt.xlabel('Tiempo (s)')
    plt.ylabel('Caudal (m³/s)')
    plt.title('Gráfico de Caudal en función del Tiempo')
    plt.legend()

    graph_path = os.path.join('app', 'static', 'caudal_graph.png')
    plt.savefig(graph_path)
    plt.close()
    return graph_path

def generar_dem_solo(dsm_path):
    image = gdal.Open(dsm_path)
    band = image.GetRasterBand(1)
    z = band.ReadAsArray()
    
    nrows, ncols = z.shape
    x = np.linspace(0, ncols, ncols)
    y = np.linspace(0, nrows, nrows)
    X, Y = np.meshgrid(x, y)

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    
    ax.plot_surface(X, Y, z, cmap='gist_earth', edgecolor='none', alpha=0.9)

    ax.set_title('Modelo Digital de Terreno (DEM)')
    ax.set_xlabel('Distancia a lo largo del río (m)')
    ax.set_ylabel('Ancho del terreno (m)')
    ax.set_zlabel('Altura (m)')

    dem_path = os.path.join('app', 'static', 'dem_solo.png')
    plt.savefig(dem_path)
    plt.close()
    return dem_path


def generar_simulacion_inundacion_video(dsm_path, caudal):
    image = gdal.Open(dsm_path)
    band = image.GetRasterBand(1)
    z = band.ReadAsArray()

    nrows, ncols = z.shape
    x = np.linspace(0, ncols, ncols)
    y = np.linspace(0, nrows, nrows)
    X, Y = np.meshgrid(x, y)

    water_levels = np.linspace(0, caudal / 100, num=50)  # Simula la subida gradual del nivel de agua

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.set_title('Simulación de Inundación Dinámica')
    ax.set_xlabel('Distancia a lo largo del río (m)')
    ax.set_ylabel('Ancho del terreno (m)')
    ax.set_zlabel('Altura sobre el nivel del agua (m)')
    
    def update(frame):
        ax.clear()
        ax.plot_surface(X, Y, z, cmap='gist_earth', edgecolor='none', alpha=0.6)
        water_level = water_levels[frame]
        Z_water = np.where(z <= water_level, water_level, np.nan)
        ax.plot_surface(X, Y, Z_water, color='blue', alpha=0.5, edgecolor='none')
        ax.set_title(f'Inundación - Nivel de Agua: {water_level:.2f} m')

    anim = FuncAnimation(fig, update, frames=len(water_levels), repeat=False)

    anim_path = os.path.join('app', 'static', 'inundacion_dinamica.mp4')
    anim.save(anim_path, writer='ffmpeg', fps=10)
    
    plt.close(fig)
    return anim_path




def generar_animacion_inundacion(dsm_path, caudal):
    # Cargar el DEM
    image = gdal.Open(dsm_path)
    band = image.GetRasterBand(1)
    z = band.ReadAsArray()

    # Coordenadas del DEM
    nrows, ncols = z.shape
    x = np.linspace(0, ncols, ncols)
    y = np.linspace(0, nrows, nrows)
    X, Y = np.meshgrid(x, y)

    # Crear una serie de niveles de agua desde 0 hasta el caudal máximo
    water_levels = np.linspace(0, caudal / 10, num=60)

    # Configuración de la figura
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_title('Simulación de Inundación')
    ax.set_xlabel('Distancia a lo largo del río (m)')
    ax.set_ylabel('Ancho del terreno (m)')

    # Configurar límites y colores
    dem_plot = ax.imshow(z, cmap='terrain', extent=(0, ncols, 0, nrows), alpha=0.8)

    def update(frame):
        ax.clear()
        # Mostrar el DEM con un colormap de terreno
        ax.imshow(z, cmap='terrain', extent=(0, ncols, 0, nrows), alpha=0.8)

        # Nivel de agua basado en el caudal calculado
        water_level = water_levels[frame]
        Z_water = np.where(z <= water_level, water_level, np.nan)

        # Agregar la capa de agua en azul
        ax.imshow(Z_water, cmap='Blues', alpha=0.5, extent=(0, ncols, 0, nrows))

        # Títulos y etiquetas
        ax.set_title(f'Simulación de Inundación - Nivel de Agua: {water_level:.2f} m')
        ax.set_xlabel('Distancia a lo largo del río (m)')
        ax.set_ylabel('Ancho del terreno (m)')

    # Crear animación
    anim = FuncAnimation(fig, update, frames=len(water_levels), repeat=False)
    anim_path = os.path.join('app', 'static', 'simulacion_inundacion.mp4')
    anim.save(anim_path, writer='ffmpeg', fps=10)

    plt.close(fig)
    return anim_path





@bp.route('/resultado')
def resultado():
    fecha = request.args.get('fecha')
    caudal = request.args.get('caudal')
    graph_path = url_for('static', filename=os.path.basename(request.args.get('graph_path')))
    sim_path = url_for('static', filename=os.path.basename(request.args.get('sim_path')))
    dem_path = url_for('static', filename=os.path.basename(request.args.get('dem_path')))
    anim_path = url_for('static', filename=os.path.basename(request.args.get('anim_path')))
    absorcion = request.args.get('absorcion')
    drenaje = request.args.get('drenaje')

    return render_template('resultado.html', fecha=fecha, caudal=caudal, graph_path=graph_path,
                            sim_path=sim_path, dem_path=dem_path, anim_path=anim_path,
                            absorcion=absorcion, drenaje=drenaje)
