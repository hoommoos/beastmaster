#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import os
import argparse
import urllib
import shutil
import docker
import random
import urllib.request
from time import sleep as delay

SCRIPT_NAME = 'beastmaster'

parser = argparse.ArgumentParser(description='Run instances with selected parameters.')

parser.add_argument('--run', '-r', help='Build an image if not build yet and run all instances.',
                    nargs='?',
                    type=int,
                    const=True,
                    default=0
                    )

parser.add_argument('--update', '-u', help='Make git pull from script dir and update script.',
                    nargs='?',
                    type=int,
                    const=True,
                    default=0
                    )

parser.add_argument('--rm', help='Remove and stop all running containers.',
                    nargs='?',
                    type=bool,
                    const=True,
                    default=False
                    )

parser.add_argument('--rmi', help='Remove all created images.',
                    nargs='?',
                    type=bool,
                    const=True,
                    default=False
                    )

parser.add_argument('--destroy', help='Destroy all images, containers and images and self remove all scripts and files.',
                    nargs='?',
                    type=bool,
                    const=True,
                    default=False
                    )

parser.add_argument('--delay', help='Make delay between running instances (secs). Default: 0.',
                    nargs='?',
                    type=int,
                    const=True,
                    default=0
                    )


class InstanceRunner:
    def __init__(self, accounts_file):
        self.client = docker.APIClient()

        self.accounts_file_path = os.path.abspath(accounts_file)

        self.server_ip = (
            urllib.request.urlopen("https://ipinfo.io/ip").read().decode("utf-8")
        )

        self.credentials = {}

    def parse_file(self):
        """Parse accounts.txt file in root directory to iterable dict"""
        filepath = self.accounts_file_path
        if os.path.exists(filepath):
            with open(filepath) as f:
                content = f.readlines()
                content = [x.strip() for x in content]
                for line in content:
                    split_line = line.split(";")
                    self.credentials.update({split_line[0]: split_line[1]})
        else:
            raise FileNotFoundError("File accounts.txt was not found.")

    def run_instance(self, login, password, sleep=0):
        """Run each credentials pair to a docker instance"""
        instance_name = login.split("@")[0].upper() + "_INSTANCE"
        random_port = random.randrange(2838, 3181)
        instance_addr = "http://" + str(self.server_ip) + ":" + str(random_port)
        base_command = (
            "docker run -d --name {0}"
            " -e TIDAL_LOGIN={1} -e TIDAL_PASSWORD={2}"
            " -e INSTANCE_NAME={0} -e INSTANCE_PORT={3}"
            " --restart=always"
            " -p {3}:80"
            " -v /dev/shm:/dev/shm tidal-bot -h {0} -l {4}".format(
                instance_name, login, password, random_port, instance_addr
            )
        )
        subprocess.check_output(base_command, shell=True, universal_newlines=True)

        print(instance_addr)

        if sleep > 0:
            print('\nSleeping {0} secs...\n'.format(str(sleep)))
            delay(sleep)

    def check_instances(self) -> bool:
        """Check already running instances"""
        existing_accounts = [mail.split("@")[0] for mail in self.credentials.keys()]
        running_instances = [
            inst_name.get("Names")[0][1:].strip("_instance").lower()
            for inst_name in self.client.containers(all=False)
        ]
        if any(existing_accounts) == any(running_instances):
            return True
        else:
            return False

    def start(self, sleep=0):
        self.parse_file()
        for k, v in self.credentials.items():
            self.run_instance(k, v, sleep=sleep)

    print('Done.\n---\n')


instance = InstanceRunner(accounts_file="accounts.txt")


def remove_file(path):
    try:
        os.remove(path)
    except OSError:
        pass


def check_integrity():
    print('\n---\nChecking integrity was started.')
    if not os.path.exists('/root/accounts.txt'):
        os.mknod('/root/accounts.txt')

    if os.path.exists('/root/{0}/accounts.txt'.format(SCRIPT_NAME)):
        os.remove('/root/{0}/accounts.txt'.format(SCRIPT_NAME))
        os.symlink('/root/accounts.txt', '/root/{0}/accounts.txt'.format(SCRIPT_NAME))

    if os.path.exists('/root/accounts.txt') and os.stat("/root/accounts.txt").st_size == 0:
        print('[WARNING]: Need to fill out accounts.txt file.')

    if os.path.exists('/root/accounts.txt'):
        try:
            os.symlink('/root/accounts.txt', '/root/{0}/accounts.txt'.format(SCRIPT_NAME))
        except FileExistsError:
            print('Accounts file link already exists. Skip.')
    else:
        pass

    # Git settings
    if not os.path.isfile('/root/.git_credentials'):
        os.mknod('/root/.git_credentials')
    else:
        if os.stat("/root/.git_credentials").st_size == 0:
            print('[WARNING]: Git credentials file was found, but empty.')

    print('Done.\n---\n')


def run_silent(command):
    # subprocess.check_output(command, shell=True, universal_newlines=True)
    try:
        subprocess.call(command, shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    except FileNotFoundError:
        pass
    finally:
        print('Done.\n---\n')


def run_command(command):
    try:
        subprocess.call(command, shell=True)
    finally:
        print('Done.\n---\n')


def clean_all_containers():
    """Stop and remove all running and active containers"""
    print('\n---\nSelected to stop all active containers.')
    run_command('docker container stop $(docker container ls -aq)')

    print('\n---\nSelected to remove all active containers.')
    run_silent('docker container rm $(docker container ls -aq)')


def clean_images():
    print('---\n\nSelected to remove (purge) all images.')
    run_command('docker image prune -a')


def update():
    print("\n---\nTrying to update script via git...")
    run_silent('git pull')


def run_instances(run_delay=parser.parse_args().delay):
    print("\n---\nTrying to build image if not build yet...")
    if os.path.isfile('Dockerfile'):
        run_command("docker build -t tidal-bot .")
    if os.stat("/root/accounts.txt").st_size == 0:
        print('[ERROR]: Accounts file is empty.')
    else:
        if run_delay > 0:
            print('Started instances with delay of {0} secs.'.format(str(delay)))
        instance.start(sleep=run_delay)


def destroy():
    print('[WARNING]: All data and files including this script will be removed.')
    clean_all_containers()
    clean_images()

    remove_file('/root/.bash_history')
    remove_file('/root/.git_credentials')
    remove_file('/root/accounts.txt')
    remove_file('/root/setup.sh')

    shutil.rmtree('/root/{0}'.format(SCRIPT_NAME), ignore_errors=True)
    print('Done.')


def clean_privacy():
    print('Cleaning up private data')
    remove_file('/root/{0}/Dockerfile'.format(SCRIPT_NAME))


if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    print('\n\nStarted Instance Runner Script')
    print('Current hostname address is [{0}]\n'.format(urllib.request.urlopen("https://ipinfo.io/ip").read().decode("utf-8")))

    check_integrity()

    if parser.parse_args().rm:
        clean_all_containers()
    if parser.parse_args().rmi:
        clean_images()
    if parser.parse_args().update:
        update()
    if parser.parse_args().run:
        run_instances()
        clean_privacy()
    if parser.parse_args().destroy:
        destroy()


    print('\n---')
    print('Script has finished.')
    print('Exited.')