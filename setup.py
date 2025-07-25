from setuptools import setup, find_packages

setup(
    name="MQwork",
    version="0.1.0",
    description="MQTT-based emulation of a decentralized ip-based network",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Thijmen Fickweiler",
    author_email="thijmen.fickweiler@outlook.com",
    url="https://github.com/ThijmenFick/MQwork",
    packages=find_packages(),
    install_requires=[
        "paho-mqtt"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License"
    ],
    python_requires=">=3.6"
)
