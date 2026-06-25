#!/usr/bin/env python3

import aws_cdk as cdk

from stack import JournalAppStack

app = cdk.App()
JournalAppStack(app, "JournalAppStack")

app.synth()
