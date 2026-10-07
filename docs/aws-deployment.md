# AWS deployment path: EC2 + k3s + ECR + Bedrock

This document is a future deployment guide; it does not provision AWS resources.

## Low-cost target

Run a single appropriately sized Amazon EC2 instance with k3s. Store the three container images in Amazon ECR and use an instance IAM role for ECR pulls and, optionally, Amazon Bedrock inference. This avoids the cost and operational surface of EKS for an interview demo.

## Suggested sequence

1. Create an EC2 instance in a restricted security group. Expose SSH only from an administrator IP and the demo NodePort only from trusted interview/demo IPs.
2. Attach an IAM instance profile granting least-privilege ECR image pull access. Add `bedrock:InvokeModel` only when Bedrock mode is used and restrict it to the selected model.
3. Install k3s on the instance and confirm `kubectl get nodes` reports `Ready`.
4. Create private ECR repositories for `banking-service`, `agent-service`, and `frontend`.
5. Authenticate Docker to ECR, build/tag/push each image, then replace the placeholder image names in `kubernetes/*-deployment.yaml` with the ECR URIs.
6. Apply the manifests with `kubectl apply -f kubernetes/` and inspect `kubectl get pods -n bank-reconciliation`.
7. Access the Streamlit NodePort (`30080`) through the instance address or, preferably, an SSH tunnel/restricted reverse proxy.

## Bedrock mode

Build the agent image with `--build-arg INSTALL_BEDROCK=true`, set `LLM_PROVIDER=bedrock`, `AWS_REGION`, and `BEDROCK_MODEL_ID`, and allow the instance role to invoke that model. The AWS SDK automatically uses the instance role; do not place static access keys in Git, images, ConfigMaps, or `.env` files.

For a real deployment, store configuration in AWS Systems Manager Parameter Store or Secrets Manager, use TLS and authenticated ingress, persist cases/audits durably, add backup/retention policies, and implement financial-control requirements before connecting to any real banking system.
