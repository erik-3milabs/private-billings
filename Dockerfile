# Use the official Ubuntu base image
FROM ubuntu:22.04

# Set environment variables to non-interactive (this prevents some prompts)
ENV DEBIAN_FRONTEND=noninteractive

# Install necessary dependencies for OpenFHE and JupyterLab
RUN apt-get update && apt-get install -y \
    cmake \
    git \
    build-essential \
    python3 \
    python3-dev \
    python3-pip \
    python3-venv \
    sudo \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install PyBind11
RUN pip3 install "pybind11[global]"
	
# Install JupyterLab
RUN python3 -m pip install --no-cache-dir jupyterlab

# Clone and build OpenFHE-development
RUN git clone https://github.com/openfheorg/openfhe-development.git \
    && cd openfhe-development \
    && mkdir build \
    && cd build \
    && cmake -DBUILD_UNITTESTS=OFF -DBUILD_EXAMPLES=OFF -DBUILD_BENCHMARKS=OFF .. \
    && make -j$(nproc) \
    && make install

# Assume that OpenFHE installs libraries into /usr/local/lib
# Update LD_LIBRARY_PATH to include this directory
ENV LD_LIBRARY_PATH=/usr/local/lib:${LD_LIBRARY_PATH}

# Clone and build OpenFHE-Python
RUN git clone https://github.com/openfheorg/openfhe-python.git \
    && cd openfhe-python \
    && mkdir build \
    && cd build \
    && cmake .. \
    && make -j$(nproc) \
    && make install

ENV PYTHONPATH=/usr/lib/python3/dist-packages:${PYTHONPATH}

# Install the application dependencies
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy in the source code
COPY src ./src
COPY launch.py launch.py

# Setup an app user so the container doesn't run as the root user
RUN useradd app
USER app

CMD python3 launch.py $PRIVATE_BILLING_SERVER_TYPE
