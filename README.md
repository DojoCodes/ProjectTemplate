# ChallengeTemplate

Template for challenges repository.

Click on the `Use this template` button to create your own DojoCodes project !

## Scopes

This list of scopes is required for the token used in the deployment pipeline

- `challenge_read`
- `environment_read`
- `campaign_read`
- `score_read`
- `challenge_write`
- `campaign_write`
- `score_write`
- `challenge_create`
- `environment_admin`

## Using GitHub Actions to deploy project

Create a Personal Access Token using the [DojoCodes API](https://api.dojo.codes/docs) and send the following payload to the `POST /authentication/personal_access_token` route :
```json
{
  "id": "github_actions",
  "scopes": [
    "challenge_read",
    "environment_read",
    "campaign_read",
    "score_read",
    "challenge_write",
    "campaign_write",
    "score_write",
    "challenge_create",
    "environment_admin"
  ]
}
```

The response will show you the token :

```json
{
  "id": "github_actions",
  "token": "YOUR_TOKEN_TO_KEEP_PRECIOUSLY",
  "scopes": [
    "challenge_read",
    "environment_read",
    "campaign_read",
    "score_read",
    "challenge_write",
    "campaign_write",
    "score_write",
    "challenge_create"
  ]
}
```

> ⚠️ Keep it preciously, it will only be shown once !

You can then head to the [**Secret section**](settings/secrets/actions) and add the following secrets :
| Secret name | Secret value |
| ----------- | ------------ |
| `DOJO_USERNAME` | *Your Dojo username* |
| `DOJO_TOKEN` | *The token previously created* |

Now, each time you push a commit to the repository, the Dojo project will be uploaded on the dojo.codes website
