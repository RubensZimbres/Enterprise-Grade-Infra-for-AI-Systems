# modules/ingress/main.tf

# --- 1. The Shield: Cloud Armor Security Policy ---
resource "google_compute_security_policy" "security_policy" {
  name = "${var.project_id}-security-policy"

  # Adaptive Protection: Uses ML to detect and block L7 DDoS attacks
  adaptive_protection_config {
    layer_7_ddos_defense_config {
      enable = true
      rule_visibility = "STANDARD"
    }
  }

  # Rule 1: Block SQL Injection (OWASP)
  rule {
    action   = "deny(403)"
    priority = 1000
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('sqli-v33-stable')"
      }
    }
    description = "Block SQL Injection"
  }

  # Rule 2: Block XSS (Cross-Site Scripting)
  rule {
    action   = "deny(403)"
    priority = 1001
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('xss-v33-stable')"
      }
    }
    description = "Block XSS"
  }

  # Rule 3: Block Local File Inclusion (LFI)
  rule {
    action   = "deny(403)"
    priority = 1002
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('lfi-v33-stable')"
      }
    }
    description = "Block Local File Inclusion"
  }

  # Rule 4: Block Remote Command Execution (RCE)
  rule {
    action   = "deny(403)"
    priority = 1003
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('rce-v33-stable')"
      }
    }
    description = "Block Remote Command Execution"
  }

  # Rule 5: Block Protocol Attacks (HTTP Smuggling etc)
  rule {
    action   = "deny(403)"
    priority = 1004
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('protocolattack-v33-stable')"
      }
    }
    description = "Block Protocol Attacks"
  }

  # Rule 6: Block Known Scanner IPs (Nmap, Nessus etc)
  rule {
    action   = "deny(403)"
    priority = 1005
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('scannerdetection-v33-stable')"
      }
    }
    description = "Block Scanner Detection"
  }

  # Rule 10: Rate Limiting (Prevent DDoS/Brute Force)
  rule {
    action   = "rate_based_ban"
    priority = "2000"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"
      # Limit: 500 requests per minute per IP
      rate_limit_threshold {
        count        = 500
        interval_sec = 60
      }
      ban_duration_sec = 300 # Ban for 5 minutes
    }
    description = "Rate limit to prevent abuse"
  }

  # Default Rule: Allow everything else
  rule {
    action   = "allow"
    priority = "2147483647"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default allow rule"
  }
}

# --- 2. The Address: Global Static IP ---
resource "google_compute_global_address" "lb_ip" {
  name = "${var.project_id}-lb-ip"
}

# --- 3. The Bridge: Serverless NEG ---
# This connects the Load Balancer to your Cloud Run Frontend
resource "google_compute_region_network_endpoint_group" "serverless_neg" {
  name                  = "${var.project_id}-frontend-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  cloud_run {
    service = var.frontend_service_name # Comes from Compute module
  }
}

# --- 4. The Backend Service (Router + CDN + Armor) ---
resource "google_compute_backend_service" "default" {
  name      = "${var.project_id}-backend-service"
  protocol  = "HTTP" # Cloud Run talks HTTP internally
  port_name = "http"
  timeout_sec = 300

  # Attach Cloud Armor
  security_policy = google_compute_security_policy.security_policy.id

  # Enable Cloud CDN (As per your diagram)
  enable_cdn = true
  cdn_policy {
    cache_mode                   = "CACHE_ALL_STATIC"
    client_ttl                   = 3600
    default_ttl                  = 3600
    max_ttl                      = 86400
    negative_caching             = true
    serve_while_stale            = 86400

    cache_key_policy {
      include_host           = true
      include_protocol       = true
      include_query_string   = true
    }
  }

  # --- IAP CONFIGURATION ---
  iap {
    enabled              = true
    oauth2_client_id     = var.iap_client_id
    oauth2_client_secret = var.iap_client_secret
  }

  backend {
    group = google_compute_region_network_endpoint_group.serverless_neg.id
  }
}

# --- 5. SSL Certificate (Managed) ---
resource "google_compute_managed_ssl_certificate" "default" {
  name = "${var.project_id}-ssl-cert"

  managed {
    domains = [var.domain_name] # You MUST own this domain
  }
}

# --- 6. URL Map (The Traffic Director) ---
resource "google_compute_url_map" "default" {
  name            = "${var.project_id}-url-map"
  default_service = google_compute_backend_service.default.id
}

# --- 7. HTTPS Proxy ---
resource "google_compute_target_https_proxy" "default" {
  name             = "${var.project_id}-https-proxy"
  url_map          = google_compute_url_map.default.id
  ssl_certificates = [google_compute_managed_ssl_certificate.default.id]
}

# --- 8. The Front Door: Global Forwarding Rule ---
resource "google_compute_global_forwarding_rule" "default" {
  name       = "${var.project_id}-lb-forwarding-rule"
  target     = google_compute_target_https_proxy.default.id
  port_range = "443"
  ip_address = google_compute_global_address.lb_ip.address
}