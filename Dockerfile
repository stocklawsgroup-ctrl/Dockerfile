# Use Ubuntu base image
FROM ubuntu:20.04

# Avoid interactive prompts during package install
ENV DEBIAN_FRONTEND=noninteractive

# Update system and install required packages
RUN apt-get update && \
    apt-get install -y shellinabox systemd && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Set root password
RUN echo 'root:root' | chpasswd

# Expose Shell In A Box port
EXPOSE 4200

# Start Shell In A Box service
CMD ["/usr/sbin/shellinaboxd", "-t", "-s", "/:LOGIN"]
