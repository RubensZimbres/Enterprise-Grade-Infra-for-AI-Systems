#!/bin/bash
cd terraform && tfsec . --tfvars-file terraform.tfvars | grep -o 'google-[a-z0-*-]*-[a-z0-*-]*'
