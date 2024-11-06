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
    sim_path = generar_simulacion_inundacion("C:/Users/alfon/arangod/DEM.tif", intensidad)
    anim_path = generar_animacion_inundacion("C:/Users/alfon/arangod/DEM.tif", intensidad, duracion)

    return redirect(url_for('main.resultado', fecha=fecha, caudal=caudal, graph_path=graph_path,
                            sim_path=sim_path, anim_path=anim_path, absorcion=absorcion, drenaje=drenaje))

def calcular_caudal_laplace(intensidad, duracion, ancho, profundidad, pendiente, K, tau, absorcion, drenaje):
    def f_t(t):
        return K * intensidad * np.exp(-absorcion * t) * (ancho * profundidad * pendiente) / (1 + drenaje * t)

    s = 1 / tau
    integral, _ = quad(lambda t: f_t(t) * np.exp(-s * t), 0, duracion)
    return integral



def generar_grafico(intensidad, caudal, duracion):
    # Configura la gráfica
    plt.figure()
    t = np.linspace(0, duracion, 100)
    caudal_values = intensidad * np.exp(-t / duracion) * caudal  # Ejemplo de datos de caudal

    # Plotea los datos
    plt.plot(t, caudal_values, label='Caudal (m³/s)')
    plt.xlabel('Tiempo (s)')
    plt.ylabel('Caudal (m³/s)')
    plt.title('Gráfico de Caudal en función del Tiempo')
    plt.legend()

    # Guarda la imagen en la carpeta 'app/static'
    graph_path = os.path.join('app', 'static', 'caudal_graph.png')
    plt.savefig(graph_path)
    plt.close()  # Cierra la figura para liberar memoria

    return graph_path


def generar_simulacion_inundacion(dsm_path, intensidad):
    # Cargar el MDT
    image = gdal.Open(dsm_path)
    band = image.GetRasterBand(1)
    z = band.ReadAsArray()
    
    # Establecer la malla de coordenadas
    nrows, ncols = z.shape
    x = np.linspace(0, ncols, ncols)
    y = np.linspace(0, nrows, nrows)
    X, Y = np.meshgrid(x, y)

    water_level = intensidad / 10  # Ajusta la escala del nivel del agua basado en la intensidad

    # Define la topografía del agua
    Z_water = np.where(z < water_level, water_level, z)  # Asigna el nivel de agua donde sea menor que la elevación

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Superficie del DEM
    ax.plot_surface(X, Y, z, cmap='gist_earth', edgecolor='none', alpha=0.6)

    # Superficie del agua
    ax.plot_surface(X, Y, Z_water, color='blue', alpha=0.5, edgecolor='none')

    # Representación de casas junto al río
    for i in range(-int(ncols / 2) + 5, int(ncols / 2), 10):
        casa_x = [i - 1, i - 1, i + 1, i + 1, i - 1, i - 1, i + 1, i + 1]
        casa_y = [10, -10, 10, -10, 10, -10, 10, -10]
        casa_z = [0, 0, 0, 0, 2, 2, 2, 2]
        ax.plot_trisurf(casa_x, casa_y, casa_z, color='peru', edgecolor='grey', alpha=0.8)

    ax.set_title('Simulación de Inundación ')
    ax.set_xlabel('Distancia a lo largo del río (m)')
    ax.set_ylabel('Ancho del terreno (m)')
    ax.set_zlabel('Altura sobre el nivel del agua (m)')

    # Guarda la imagen en el directorio estático
    sim_path = os.path.join('app', 'static', 'inundacion_simulacion.png')
    plt.savefig(sim_path)
    plt.close()

    return sim_path

def generar_animacion_inundacion(dsm_path, intensidad, duracion):
    # Cargar el MDT
    image = gdal.Open(dsm_path)
    band = image.GetRasterBand(1)
    z = band.ReadAsArray()
    
    # Establecer la malla de coordenadas
    nrows, ncols = z.shape
    x = np.linspace(0, ncols, ncols)
    y = np.linspace(0, nrows, nrows)
    X, Y = np.meshgrid(x, y)

    water_levels = np.linspace(0, intensidad / 10, num=30)  # Generar niveles de agua para la animación

    fig, ax = plt.subplots()
    cax = ax.contourf(X, Y, z, cmap='gist_earth', alpha=0.6)  # Superficie del DEM

    ax.set_title('Animación de Inundación')
    ax.set_xlabel('Distancia a lo largo del río (m)')
    ax.set_ylabel('Ancho del terreno (m)')
    
    # Crear la función de actualización para la animación
    def update(frame):
        ax.clear()  # Limpiar el eje
        ax.contourf(X, Y, z, cmap='gist_earth', alpha=0.6)  # Re-dibujar el DEM
        water_level = water_levels[frame]
        Z_water = np.where(z < water_level, water_level, z)  # Define el nivel de agua
        ax.contourf(X, Y, Z_water, color='blue', alpha=0.5)  # Superficie del agua
        ax.set_title('Animación de Inundación - Nivel de Agua: {:.2f} m'.format(water_level))
        ax.set_xlabel('Distancia a lo largo del río (m)')
        ax.set_ylabel('Ancho del terreno (m)')

    # Crear la animación
    anim = FuncAnimation(fig, update, frames=len(water_levels), repeat=False)
    
    # Guarda la animación
    anim_path = os.path.join('app', 'static', 'animacion_inundacion.mp4')
    anim.save(anim_path, writer='ffmpeg', fps=10)
    
    plt.close(fig)
    return anim_path




@bp.route('/resultado')
def resultado():
    fecha = request.args.get('fecha')
    caudal = request.args.get('caudal')
    graph_path = url_for('static', filename=os.path.basename(request.args.get('graph_path')))
    sim_path = url_for('static', filename=os.path.basename(request.args.get('sim_path')))
    anim_path = url_for('static', filename=os.path.basename(request.args.get('anim_path')))
    absorcion = request.args.get('absorcion')
    drenaje = request.args.get('drenaje')

    return render_template('resultado.html', fecha=fecha, caudal=caudal, graph_path=graph_path,
                        sim_path=sim_path, anim_path=anim_path, absorcion=absorcion, drenaje=drenaje)
