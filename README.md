# POC - API + Lambda + Terraform

Infraestrutura AWS com Terraform para:
- API HTTP (`/find` e `/analyze`) via API Gateway
- Lambdas em Python
- Bucket S3 com `data/data.json`

## Requisitos

- Terraform `>= 1.5`
- AWS CLI configurado (`aws configure`)
- Credenciais AWS com permissão para criar:
  - Lambda
  - API Gateway v2
  - IAM Role/Policy
  - S3
- Perfil AWS válido (default: `default`)

## Variáveis

### Terraform variables

- `aws_region` (default: `us-east-1`)
- `aws_profile` (default: `default`)
- `slack_bot_token` (obrigatória, sensível)

Defina o token do Slack via variável de ambiente (não versionável):

```bash
export TF_VAR_slack_bot_token="xoxb-..."
```

Opcionalmente:

```bash
export TF_VAR_aws_region="us-east-1"
export TF_VAR_aws_profile="default"
```

## Setup rápido (exports + execução)

No diretório do projeto, exporte:

```bash
export AWS_PROFILE="default"
export AWS_REGION="us-east-1"
export TF_VAR_aws_profile="$AWS_PROFILE"
export TF_VAR_aws_region="$AWS_REGION"
export TF_VAR_slack_bot_token="xoxb-..."
```

Depois rode:

```bash
terraform init
terraform plan
terraform apply
```

## Como iniciar

No diretório do projeto:

```bash
terraform init
terraform plan
terraform apply
```

## Saídas úteis

Após o `apply`, veja os endpoints:

```bash
terraform output
terraform output api_endpoint
terraform output analyze_endpoint
```

## Testes rápidos

### 1) Endpoint `find`

```bash
curl "$(terraform output -raw api_endpoint)"
```

Exemplo manual:

```bash
curl "https://<api-id>.execute-api.us-east-1.amazonaws.com/hom/find?terminal=001"
```

### 2) Endpoint `analyze` (formato Slack)

```bash
curl -X POST "$(terraform output -raw analyze_endpoint)" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "event_callback",
    "event": {
      "type": "message",
      "channel": "C123456",
      "ts": "1710000000.000100",
      "text": "validar uuid 123e4567-e89b-12d3-a456-426614174000"
    }
  }'
```

## Integração com Slack (Lambda `analyze`)

A Lambda `hom_analyze_lambda` recebe eventos do Slack no endpoint:

```text
POST /hom/analyze
```

Origem da informação no Slack:
- Slack Events API
- Slack App -> Event Subscriptions -> Request URL
- A Request URL deve apontar para `terraform output -raw analyze_endpoint`

Quando você salva a URL no Slack, ele envia um `url_verification` para validar.
Depois disso, eventos como mensagem em canal chegam como `event_callback`.

Exemplo de request `url_verification` recebida do Slack:

```json
{
  "token": "legacy-verification-token",
  "challenge": "3eZbrw1aBm...",
  "type": "url_verification"
}
```

Exemplo de request `event_callback` recebida do Slack:

```json
{
  "token": "legacy-verification-token",
  "team_id": "T123456",
  "api_app_id": "A123456",
  "type": "event_callback",
  "event_id": "Ev123456",
  "event_time": 1710000000,
  "event": {
    "type": "message",
    "channel": "C123456",
    "user": "U123456",
    "text": "validar uuid 123e4567-e89b-12d3-a456-426614174000",
    "ts": "1710000000.000100"
  }
}
```

## Destruir recursos

```bash
terraform destroy
```

## Observações

- Não comite tokens, `*.tfvars` ou state local.
- O `.terraform.lock.hcl` deve ficar versionado para garantir versões de providers consistentes.

## Exemplo de policy IAM (Lambda `hom_analyze`)

Exemplo de permissões mínimas (substitua `<ACCOUNT_ID>` pelo valor da sua conta):

```json
{
  "Statement": [
    {
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Effect": "Allow",
      "Resource": "arn:aws:bedrock:us-east-1::foundation-model/deepseek.v3.2"
    },
    {
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Effect": "Allow",
      "Resource": "arn:aws:lambda:us-east-1:<ACCOUNT_ID>:function:hom_analyze_processor_lambda"
    },
    {
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Effect": "Allow",
      "Resource": "arn:aws:logs:us-east-1:<ACCOUNT_ID>:log-group:/aws/lambda/hom_analyze_lambda:*"
    }
  ],
  "Version": "2012-10-17"
}
```
