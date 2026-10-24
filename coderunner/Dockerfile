# Iga code runner: compiles and runs students' C++ and Java programs for the code playground.
# Built from the official GCC and Eclipse Temurin (OpenJDK) images, so nothing is downloaded when it starts.
FROM eclipse-temurin:21-jdk AS jdk

FROM gcc:15-bookworm
COPY --from=jdk /opt/java/openjdk /opt/java/openjdk
ENV JAVA_HOME=/opt/java/openjdk \
    PATH=/opt/java/openjdk/bin:$PATH \
    LANG=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
# One unprivileged user per slot: programs running at the same time can't see or signal each other.
RUN for i in 1 2 3 4 5 6 7 8; do useradd --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin --uid $((2000 + i)) "job$i"; done
WORKDIR /app
COPY server.py test_server.py ./
EXPOSE 2000
# Runs as root with only the capabilities it needs (see docker-compose.yml) to start each program as its slot's user.
CMD ["python3", "/app/server.py"]
