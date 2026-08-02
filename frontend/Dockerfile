# Hafif ve daha güncel bir Node.js imajı kullanıyoruz (18 yerine 20)
FROM node:20-slim

# Konteyner içindeki çalışma dizini
WORKDIR /app

# Önce sadece paket dosyalarını kopyalayarak npm install adımını önbelleğe alıyoruz
COPY package*.json ./
RUN npm install

# Kalan tüm dosyaları kopyalıyoruz
COPY . .

# Docker içinden dışarıya (localhost'a) yayın yapabilmek için HOST ayarı
ENV HOST=0.0.0.0
ENV PORT=3000

# Geliştirme sunucusunu başlatıyoruz
CMD ["npm", "run", "dev"]