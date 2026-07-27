# Key custody

## Two different keys — the distinction that decides everything

Almost all bad advice about lost keystores comes from conflating these.

| Key | Who holds it | If lost |
|-----|--------------|---------|
| **Upload key** — what this skill generates | You | **Recoverable.** Generate a new key, export its certificate, and request an upload key reset in Play Console (App signing → Upload key certificate → Request upload key reset). Google processes it in about two days. Users are unaffected; the app signing key never changed. |
| **App signing key** — what Play uses to sign what users install | Google, under Play App Signing | Not your problem; Google holds it. |
| **App signing key**, if you opted out of Play App Signing | You | **Unrecoverable.** Android verifies every update against the original certificate. No new key is accepted. You must publish a new app under a new application ID, losing installs, ratings, and reviews. |

Play App Signing is required for all new apps since August 2021, so for anything created today the local keystore is an **upload key** and losing it is a two-day inconvenience, not a catastrophe.

Say this accurately. The widespread "lose your keystore and your app is dead" warning applies to the third row only, and repeating it for an enrolled app is false alarm — it also teaches the user to distrust the next warning, which may be the real one.

What is genuinely unrecoverable, in every case: **a leaked key**. Anyone holding the upload key and its password can publish a build as the developer until the reset lands. Confidentiality matters more than availability here.

## Storing it

The keystore and its passwords must survive: the disk dying, the laptop being stolen, and the project directory being deleted.

**Primary — a password manager** (1Password, Bitwarden, KeePassXC). Store as one entry:

- the `.jks` file as an attachment
- `storePassword`, `keyPassword`, `keyAlias`
- the SHA-1 and SHA-256 fingerprints
- the application ID it belongs to

Keeping them in one entry matters. A keystore recovered without its password is as useless as no keystore.

**Secondary — an encrypted archive off the machine:**

```bash
tar czf - android/app/upload-keystore.jks android/key.properties \
  | gpg -c --cipher-algo AES256 > upload-key-backup.tar.gz.gpg
```

Then move it somewhere else entirely — another machine, cloud storage, external drive. Store the passphrase in the password manager, not with the archive.

**Not a backup:**

- A copy in `~/.flutter-keys/` — same disk, dies with it
- Plaintext password files sitting next to the keystore — one compromise takes both
- The project repo — see `.gitignore`, and note that private repos get forked, cloned, and made public
- Any chat or email thread

If a local convenience copy is kept anyway, at minimum separate the secrets: `chmod 700` the directory, and keep the passwords only in the password manager.

## Multiple apps

One keystore can hold keys for several apps, or each app can have its own file. Per-app keystores are easier to reason about and limit the blast radius of a leak; a shared keystore is fewer things to lose. Either is defensible — what matters is that the record says which alias belongs to which application ID.

## Rotation

There is no routine rotation for signing keys — the certificate is the app's identity. Generate a new upload key only when:

- the current one is compromised (leaked, committed, shared)
- it is nearing expiry (Play requires validity past 22 Oct 2033)

In both cases the path is an upload key reset in Play Console, not a new app.

## What to tell the user

At the end of the run, state plainly: the key exists only on this machine, backing it up is theirs to do, and here is exactly what to put in the password manager. A report claiming the backup is done when it wrote a file next to the original is the failure mode this section exists to prevent.
