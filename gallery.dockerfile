FROM python:3.12-alpine
WORKDIR /app
COPY gallery.py
RUN pip install cerberus
RUN pip install requests
RUN pip install pillow
EXPOSE 8000
CMD ["python", "gallery.py"]