import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from shiny.express import input, render, ui
from scipy.stats import norm

# Page configuration
ui.page_opts(title="California House Values — Spatial Clusters", fillable=True)

# --- SIDEBAR FILTERS ---
with ui.sidebar(width=300):
    ui.markdown("### Filters")
    ui.input_checkbox_group(
        "proximity", "Ocean Proximity", 
        {"inland": "Inland", "coastal": "Coastal", "bay": "Near Bay"},
        selected=["bay"]
    )
    ui.input_slider("home_range", "Home Range ($)", 0, 500000, [100000, 400000])
    ui.input_slider("income_range", "Income Range ($)", 0, 150000, [20000, 80000])
    ui.input_slider("age", "Housing Age", 0, 50, 25)
    
    ui.hr()
    ui.markdown("### Map Controls")
    ui.input_radio_buttons("view", "View:", ["Points", "Hexbins"], selected="Hexbins", inline=True)
    ui.input_slider("opacity", "Opacity", 0.0, 1.0, 0.7)
    ui.input_action_button("recompute", "Recompute", class_="btn-primary w-100")

# --- MAIN CONTENT ---
with ui.layout_columns(col_widths=[8, 4]):
    
    # Left Column: The Map
    with ui.card(full_screen=True):
        ui.card_header("California Map")
        
        @render.plot
        def map_plot():
            fig, ax = plt.subplots(figsize=(8, 10))
            x = np.random.randn(500)
            y = np.random.randn(500)
            hb = ax.hexbin(x, y, gridsize=20, cmap='BuGn', alpha=input.opacity())
            ax.set_axis_off()
            return fig

    # Right Column: Statistics & Distributions
    with ui.layout_column_wrap(width=1, gaps="10"):
        
        # Table Comparison
        with ui.card():
            ui.card_header("Selected Region vs State")
            @render.table
            def stats_table():
                data = {
                    "Metric": ["Median Value", "Median Income"],
                    "Selected": ["$320K", "$65K"],
                    "Statewide": ["$520K", "$65K"]
                }
                return pd.DataFrame(data)

        # Distribution Plots
        with ui.card():
            ui.card_header("House Value Distribution")
            @render.plot(height=150)
            def value_dist():
                fig, ax = plt.subplots()
                x = np.linspace(-4, 4, 100)
                y = norm.pdf(x, 0, 1)
                ax.plot(x, y, color="orange")
                ax.fill_between(x, y, color="orange", alpha=0.2)
                ax.set_axis_off()
                return fig

        with ui.card():
            ui.card_header("Income Distribution")
            @render.plot(height=150)
            def income_dist():
                fig, ax = plt.subplots()
                x = np.linspace(-4, 4, 100)
                y = norm.pdf(x, 0, 1)
                ax.plot(x, y, color="blue")
                ax.fill_between(x, y, color="blue", alpha=0.2)
                ax.set_axis_off()
                return fig