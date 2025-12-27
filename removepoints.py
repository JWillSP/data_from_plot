import streamlit as st
import pandas as pd
import altair as alt

# Sample data
df = pd.DataFrame({
    'x': [1, 2, 3, 4, 5],
    'y': [10, 20, 15, 25, 30]
})

# Select point to remove
point_to_remove = st.number_input("Remove point with x =", min_value=1, max_value=5, step=1)

# Filter out the selected point
filtered_df = df[df['x'] != point_to_remove]

# Plot updated chart
chart = alt.Chart(filtered_df).mark_circle(size=100).encode(
    x='x',
    y='y'
)

st.altair_chart(chart, use_container_width=True)
