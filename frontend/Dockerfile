# Use Node.js LTS (Alpine for smaller size)
FROM node:20-alpine

# Set the working directory
WORKDIR /app

# Copy package.json and package-lock.json first to leverage Docker cache
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the frontend source code
COPY . .

# Expose the dev server port (3000 as defined in vite.config.js)
EXPOSE 3000

# Start the Vite development server ensuring it binds to 0.0.0.0
CMD ["npm", "run", "dev"]
