import sys
try:
    from PIL import Image
    import collections

    img = Image.open('/home/runner/work/profit2k12-odoo/profit2k12-odoo/images/photo-1791460612-1.jpg')
    img = img.convert('RGB')
    img.thumbnail((100, 100))
    colors = img.getcolors(10000)
    colors.sort(key=lambda x: x[0], reverse=True)
    
    print("Non-grayscale colors:")
    for count, (r, g, b) in colors:
        if abs(r-g) > 20 or abs(r-b) > 20 or abs(g-b) > 20: # skip grays
            hex_color = '#%02x%02x%02x' % (r, g, b)
            print(f"Count: {count}, Color: {hex_color} - RGB: ({r}, {g}, {b})")
except Exception as e:
    print(f"Error: {e}")
