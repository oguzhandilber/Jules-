# Use official Nginx image
FROM nginx:alpine

# Copy static assets from frontend directory in the build context
COPY ./frontend/ /usr/share/nginx/html/

# Copy custom Nginx configuration
COPY ./frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
