FROM python:3.12-alpine
WORKDIR /app
COPY gallery.py .
COPY images/ ./images
RUN pip install cerberus
RUN pip install requests
RUN pip install pillow
EXPOSE 8000
<<<<<<< HEAD
CMD ["python", "gallery.py"]
=======
CMD ["python", "gallery.py"]
>>>>>>> refs/remotes/origin/main
