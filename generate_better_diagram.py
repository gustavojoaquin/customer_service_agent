"""
Script para generar un diagrama completo del grafo de LangGraph
Ejecutar: python generate_better_diagram.py
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import networkx as nx

def create_detailed_diagram():
    # Crear figura grande
    fig, ax = plt.subplots(figsize=(20, 16))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis('off')
    
    # Colores para cada tipo de nodo
    colors = {
        'start': '#4CAF50',
        'primary': '#2196F3',
        'assistant': '#FF9800',
        'tools_safe': '#9C27B0',
        'tools_sensitive': '#F44336',
        'entry': '#00BCD4',
        'leave': '#795548'
    }
    
    # Función para dibujar nodo
    def draw_node(x, y, label, color, width=1.5, height=0.5):
        box = FancyBboxPatch(
            (x - width/2, y - height/2), width, height,
            boxstyle="round,pad=0.1",
            facecolor=color,
            edgecolor='black',
            linewidth=2,
            alpha=0.8
        )
        ax.add_patch(box)
        ax.text(x, y, label, ha='center', va='center', 
                fontsize=9, weight='bold', color='white')
    
    # Función para dibujar flecha
    def draw_arrow(x1, y1, x2, y2, style='solid', color='black', label=''):
        arrow = FancyArrowPatch(
            (x1, y1), (x2, y2),
            arrowstyle='->', 
            mutation_scale=20,
            linewidth=2,
            linestyle=style,
            color=color,
            alpha=0.7
        )
        ax.add_patch(arrow)
        if label:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(mx, my, label, fontsize=7, 
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # NIVEL 1: START y fetch_user_info
    draw_node(5, 11, 'START', colors['start'])
    draw_node(5, 10, 'fetch_user_info', colors['primary'])
    draw_arrow(5, 10.75, 5, 10.25)
    
    # NIVEL 2: Primary Assistant
    draw_node(5, 8.5, 'primary_assistant', colors['primary'], width=2)
    draw_arrow(5, 9.75, 5, 8.75)
    
    # NIVEL 3: Primary Tools
    draw_node(5, 7, 'primary_tools_node', colors['tools_safe'])
    draw_arrow(5, 8.25, 5, 7.25, label='tools')
    draw_arrow(5, 6.75, 5, 8.25, style='dashed', label='back')
    
    # NIVEL 4: Entry nodes para cada asistente
    y_entries = 5.5
    x_positions = [1.5, 3.5, 6.5, 8.5]
    entry_labels = [
        'enter_flight_assistant',
        'enter_hotel_assistant', 
        'enter_car_rental_assistant',
        'enter_excursion_assistant'
    ]
    
    for i, (x, label) in enumerate(zip(x_positions, entry_labels)):
        draw_node(x, y_entries, label, colors['entry'], width=1.8, height=0.6)
        # Flechas desde primary_assistant a entry nodes
        draw_arrow(5, 8.25, x, y_entries + 0.3, color='blue')
    
    # NIVEL 5: Asistentes especializados
    y_assistants = 4
    assistant_labels = [
        'flight_assistant',
        'hotel_assistant',
        'car_rental_assistant', 
        'excursion_assistant'
    ]
    
    for x, label in zip(x_positions, assistant_labels):
        draw_node(x, y_assistants, label, colors['assistant'], width=1.8)
        draw_arrow(x, y_entries - 0.3, x, y_assistants + 0.25)
    
    # NIVEL 6: Safe tools
    y_safe = 2.5
    safe_labels = [
        'flight_safe_tools',
        'hotel_safe_tools',
        'car_rental_safe_tools',
        'excursion_safe_tools'
    ]
    
    for x, label in zip(x_positions, safe_labels):
        draw_node(x, y_safe, label, colors['tools_safe'], width=1.6, height=0.5)
        # Flecha asistente -> safe tools
        draw_arrow(x, y_assistants - 0.25, x, y_safe + 0.25, color='purple')
        # Flecha safe tools -> asistente (back)
        draw_arrow(x - 0.3, y_safe + 0.25, x - 0.3, y_assistants - 0.25, 
                  style='dashed', color='purple')
    
    # NIVEL 7: Sensitive tools
    y_sensitive = 1
    sensitive_labels = [
        'flight_sensitive_tools',
        'hotel_sensitive_tools',
        'car_rental_sensitive_tools',
        'excursion_sensitive_tools'
    ]
    
    for x, label in zip(x_positions, sensitive_labels):
        draw_node(x, y_sensitive, label, colors['tools_sensitive'], 
                 width=1.6, height=0.5)
        # Flecha asistente -> sensitive tools
        draw_arrow(x, y_assistants - 0.25, x, y_sensitive + 0.25, color='red')
        # Flecha sensitive tools -> asistente (back)
        draw_arrow(x + 0.3, y_sensitive + 0.25, x + 0.3, y_assistants - 0.25,
                  style='dashed', color='red')
    
    # NIVEL 8: leave_skill (central)
    draw_node(5, 6.5, 'leave_skill', colors['leave'], width=1.2)
    
    # Flechas desde asistentes a leave_skill
    for x in x_positions:
        draw_arrow(x, y_assistants - 0.25, 5, 6.75, 
                  color='brown', label='complete')
    
    # Flecha de leave_skill de vuelta a primary_assistant
    draw_arrow(5, 6.25, 5, 8.25, style='dashed', color='brown', label='escalate')
    
    # END nodes
    for i, x in enumerate(x_positions):
        draw_node(x, 0, 'END', colors['start'], width=0.8, height=0.4)
        draw_arrow(x, y_assistants - 0.25, x, 0.2, 
                  color='green', style='dotted')
    
    # Leyenda
    legend_elements = [
        mpatches.Patch(color=colors['start'], label='Start/End'),
        mpatches.Patch(color=colors['primary'], label='Primary nodes'),
        mpatches.Patch(color=colors['assistant'], label='Assistant nodes'),
        mpatches.Patch(color=colors['entry'], label='Entry nodes'),
        mpatches.Patch(color=colors['tools_safe'], label='Safe tools'),
        mpatches.Patch(color=colors['tools_sensitive'], label='Sensitive tools (interrupt)'),
        mpatches.Patch(color=colors['leave'], label='Leave/Escalate'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
    
    # Título
    plt.title('Customer Service Agent - LangGraph Flow\n(Complete Diagram)', 
             fontsize=16, weight='bold', pad=20)
    
    # Guardar
    plt.tight_layout()
    plt.savefig('langgraph_complete_diagram.png', dpi=300, bbox_inches='tight')
    print("✅ Diagrama guardado como: langgraph_complete_diagram.png")
    plt.show()

if __name__ == "__main__":
    print("Generando diagrama completo del grafo...")
    create_detailed_diagram()