# Stage 1: Build the React application
FROM node:18-alpine as build

# Set the working directory
WORKDIR /app

# Copy package.json and package-lock.json (or yarn.lock)
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application source code
COPY . .

# Build the application for production
RUN npm run build

# Stage 2: Serve the application using a lightweight web server
FROM nginx:stable-alpine

# Copy the built static files from the build stage to the Nginx server directory
COPY --from=build /app/build /usr/share/nginx/html

# Expose port 80 for the Nginx server
EXPOSE 80

# The Nginx image will automatically start the server
CMD ["nginx", "-g", "daemon off;"]