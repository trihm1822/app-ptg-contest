# ==============================================================================
# PTG Isolated C++17 Runner Image
# Used exclusively for compiling and running untrusted C++ code in sandbox
# ==============================================================================

FROM debian:bookworm-slim

# Avoid interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install g++ (C++17 support), libstdc++, and core utilities (timeout, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ \
    coreutils \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged sandbox user (UID 10001) with no sudo/root privileges
RUN groupadd -g 10001 sandbox && \
    useradd -u 10001 -g sandbox -m -s /bin/bash sandbox

# Set working directory to /workspace
WORKDIR /workspace

# Switch to unprivileged user by default
USER sandbox

CMD ["/bin/bash"]
