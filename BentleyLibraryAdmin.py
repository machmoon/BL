import requests
from tkinter import *
from tkinter import filedialog
from PIL import Image, ImageTk
import datetime
import io
import pandas as pd
from openpyxl import Workbook
import xlsxwriter
import mysql.connector
from Credentials import db_config

mydb = mysql.connector.connect(**db_config)


def list_to_string(lst):
    if len(lst) == 1:
        return str(lst[0])
    else:
        return ", ".join(map(str, lst))


def getTitle(ISBN):
    response = requests.get(
        f"https://www.googleapis.com/books/v1/volumes?q=isbn:{ISBN}"
    )
    data = response.json()
    title = data["items"][0]["volumeInfo"]["title"]
    return title


def getAuthor(ISBN):
    response = requests.get(
        f"https://www.googleapis.com/books/v1/volumes?q=isbn:{ISBN}"
    )
    data = response.json()
    try:
        author = data["items"][0]["volumeInfo"]["authors"]
    except:
        author = ["Unknown"]
    authorString = list_to_string(author)
    return authorString


def getPub(ISBN):
    response = requests.get(
        f"https://www.googleapis.com/books/v1/volumes?q=isbn:{ISBN}"
    )
    data = response.json()
    try:
        pub = data["items"][0]["volumeInfo"]["publisher"]
    except:
        pub = "Unknown"
    return pub


def getPubDate(ISBN):
    response = requests.get(
        f"https://www.googleapis.com/books/v1/volumes?q=isbn:{ISBN}"
    )
    data = response.json()
    pub_date_str = data["items"][0]["volumeInfo"]["publishedDate"]

    # Attempt to parse the publication date string
    try:
        pub_date = datetime.datetime.strptime(pub_date_str, "%Y-%m-%d").date()
    except ValueError:
        # If parsing fails, use a default date of 1900-01-01
        pub_date = datetime.date(1900, 1, 1)

    return str(pub_date)


def getThumbnail(ISBN):
    response = requests.get(
        f"https://www.googleapis.com/books/v1/volumes?q=isbn:{ISBN}"
    )
    data = response.json()
    try:
        thumbnail = data["items"][0]["volumeInfo"]["imageLinks"]["thumbnail"]
        response = requests.get(thumbnail)
        thumbnail_image = Image.open(io.BytesIO(response.content))
        return thumbnail_image
    except:
        return Image.open("default-thumbnail.jpeg")


def getDes(ISBN):
    response = requests.get(
        f"https://www.googleapis.com/books/v1/volumes?q=isbn:{ISBN}"
    )
    data = response.json()
    try:
        des = data["items"][0]["volumeInfo"]["description"]
    except:
        des = "None"
    return des

def getImg(ISBN):
    response = requests.get(
        f"https://www.googleapis.com/books/v1/volumes?q=isbn:{ISBN}"
    )
    data = response.json()
    try:
        img = data["items"][0]["volumeInfo"]["imageLinks"]["thumbnail"]
    except:
        img = "https://www.google.com/url?sa=i&url=https%3A%2F%2Fen.m.wikipedia.org%2Fwiki%2FFile%3APlaceholder_book.svg&psig=AOvVaw0rpcntiVilGdXwo31ikPLC&ust=1696497214595000&source=images&cd=vfe&ved=0CBAQjRxqFwoTCIC4ieGG3IEDFQAAAAAdAAAAABAE"
    return img


def add_book():
    isbn = isbn_entry.get()
    quantity = quantity_entry.get()
    # try:
    title = getTitle(isbn)
    author = getAuthor(isbn)
    publication_date = getPubDate(isbn)
    thumbnail = getThumbnail(isbn)
    thumbnail = thumbnail.resize((300, 450))
    thumbnail_image = ImageTk.PhotoImage(thumbnail)
    query = (
        "INSERT INTO bookinventory (title, author, isbn, published_date, publisher, quantity, available_quantity, description, image_url)"
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )
    data = (
        title,
        author,
        isbn,
        publication_date,
        getPub(isbn),
        quantity,
        quantity,
        getDes(isbn),
        getImg(isbn),
    )
    cursor = mydb.cursor()
    cursor.execute(query, data)
    mydb.commit()
    status_label.config(text="Book inserted successfully.", fg="green")
    thumbnail_label.config(image=thumbnail_image)
    thumbnail_label.image = thumbnail_image
    # except:
    #     status_label.config(text="Error inserting book", fg="red")


def export_to_excel():
    # Prompt user to select a location to save the file
    filename = filedialog.asksaveasfilename(
        defaultextension=".xlsx", filetypes=(("Excel Files", "*.xlsx"),)
    )

    if filename:
        query = "SELECT * FROM bookinventory"
        df_bookinventory = pd.read_sql(query, mydb)

        # Read data from the log table
        query = "SELECT * FROM log"
        df_log = pd.read_sql(query, mydb)

        # Create a Pandas Excel writer using XlsxWriter as the engine
        writer = pd.ExcelWriter(filename, engine="xlsxwriter")

        # Write each dataframe to a different worksheet
        df_bookinventory.to_excel(writer, sheet_name="Book Inventory", index=False)
        df_log.to_excel(writer, sheet_name="Log", index=False)

        # Close the Pandas Excel writer and MySQL connection
        writer.save()


# Define colors
bg_color = "#FFFFFF"
primary_color = "#FFA500"
secondary_color = "#333333"

# Create the main window
root = Tk()
root.title("Bentley Library")
root.geometry("800x600")
root.configure(bg=bg_color)

# Create the header frame
header_frame = Frame(root, bg=primary_color, pady=10)
header_frame.pack(fill=X)

# Create the header logo
logo_image = Image.open("phoenix.png")
logo_image = logo_image.resize((100, 100))
logo_photo = ImageTk.PhotoImage(logo_image)
logo_label = Label(header_frame, image=logo_photo, bg=primary_color)
logo_label.pack(side=LEFT, padx=10)

# Create the header title and subtitle
title_label = Label(
    header_frame,
    text="Bentley Library",
    font=("Arial", 24, "bold"),
    fg=bg_color,
    bg=primary_color,
)
title_label.pack(side=LEFT, padx=10)
# subtitle_label = Label(header_frame, text="Explore, learn, and grow.", font=("Arial", 16), fg=bg_color, bg=primary_color)
# subtitle_label.pack(side=LEFT, padx=10)

# Create the main content frame
content_frame = Frame(root, bg=bg_color, padx=50, pady=50)
content_frame.pack(fill=BOTH, expand=True)

# Create the ISBN label and entry
isbn_label = Label(
    content_frame, text="ISBN", font=("Arial", 14), fg=secondary_color, bg=bg_color
)
isbn_label.pack()
isbn_entry = Entry(content_frame, font=("Arial", 14))
isbn_entry.pack()

# Create the quantity label and entry
quantity_label = Label(
    content_frame, text="Quantity", font=("Arial", 14), fg=secondary_color, bg=bg_color
)
quantity_label.pack()
quantity_entry = Entry(content_frame, font=("Arial", 14))
quantity_entry.pack()

# Create the add book button
add_book_button = Button(
    content_frame,
    text="Add Book",
    font=("Arial", 14),
    bg=bg_color,
    fg='#000000',
    padx=10,
    pady=5,
    command=add_book,
)
add_book_button.pack(pady=20)

# Create the thumbnail label
thumbnail_label = Label(content_frame, bg=bg_color)
thumbnail_label.pack()

# Create the status label
status_label = Label(content_frame, font=("Arial", 14), fg=secondary_color, bg=bg_color)
status_label.pack(pady=20)

# Create a button to export the data to Excel
export_button = Button(root, text="Export to Excel", command=export_to_excel)
export_button.pack()

# Run the main loop
root.mainloop()