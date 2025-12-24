import qrcode

# QR 1
qr1 = qrcode.QRCode(
    version=1,  # controls size (1–40)
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=10,
    border=4,
)
qr1.add_data("left")
qr1.make(fit=True)
img1 = qr1.make_image(fill_color="black", back_color="white")
img1.save("left_qr_1.png")

# QR 2 (same data, different mask/error correction)
qr2 = qrcode.QRCode(
    version=2,  # slightly larger
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=8,
    border=3,
)
qr2.add_data("left")
qr2.make(fit=True)
img2 = qr2.make_image(fill_color="black", back_color="white")
img2.save("left_qr_2.png")

print("✅ Two QR codes saved as left_qr_1.png and left_qr_2.png")