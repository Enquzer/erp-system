import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def export_to_pdf(order, filename):
    c = canvas.Canvas(filename, pagesize=letter)
    c.setFont("Helvetica", 12)
    c.drawString(100, 750, f"Order Number: {order.get('order_number', 'N/A')}")
    c.drawString(100, 730, f"Product: {order.get('product_name', 'N/A')}")
    c.drawString(100, 710, f"Description: {order.get('product_description', 'N/A')}")
    c.drawString(100, 690, f"Color: {order.get('color', 'N/A')}")
    c.drawString(100, 670, f"Size: {order.get('size', 'N/A')}")
    c.drawString(100, 650, f"Quantity: {order.get('quantity', 0)}")
    c.drawString(100, 630, f"Order Date: {order.get('order_date', 'N/A')}")
    c.drawString(100, 610, f"Status: {order.get('status', 'N/A')}")
    c.save()

def export_to_excel(order, filename):
    data = {
        "Order Number": [order.get('order_number', 'N/A')],
        "Product Name": [order.get('product_name', 'N/A')],
        "Description": [order.get('product_description', 'N/A')],
        "Color": [order.get('color', 'N/A')],
        "Size": [order.get('size', 'N/A')],
        "Quantity": [order.get('quantity', 0)],
        "Order Date": [order.get('order_date', 'N/A')],
        "Status": [order.get('status', 'N/A')]
    }
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)