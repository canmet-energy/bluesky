# AWS Network Architecture Guide
## Executive Summary
This organization uses AWS Landing Zone with centralized networking through Transit Gateways instead of traditional Internet Gateways. Most AWS services work normally with only 2 networking restrictions.

## Quick Reference
### ✅ What Works (Full Functionality)
* All AWS Services: EC2, S3, Lambda, RDS, IAM, Route53, CloudFormation
* Infrastructure-as-Code: Complete CloudFormation support
* Networking: VPC creation, subnets, security groups, load balancers
* Internet Access: Automatic via Transit Gateway (no configuration needed)
* SSL/TLS: All certificate issues resolved in devcontainer
### ❌ What's Blocked (2 Items Only)
* Internet Gateways: Cannot create (organizational SCP policy)
* NAT Gateways: Cannot create (organizational SCP policy)
## Network Architecture
### Current Setup
* Account: 834599497928 (ca-central-1)
* VPC: vpc-0809102c90503ef2d (10.71.64.0/24)
* Subnets: 2 private subnets across AZs
* Internet Access: Transit Gateway (tgw-0368e0eab67d69402)
* AWS Services: VPC Endpoint (vpce-066ce0c2c7f5d4a55)
### Traffic Flow
Instance → Private Subnet → Transit Gateway → Internet
Instance → VPC Endpoint → AWS Services

## Development Guidelines
### Infrastructure Development
1. Use CloudFormation - Full functionality available
1. Deploy to private subnets - Internet access automatic via Transit Gateway
1. Avoid Internet/NAT Gateways - Use existing Transit Gateway routing
1. Leverage VPC Endpoints - AWS service access optimized

### Recommended Patterns
* boto3/Python: Preferred for programmatic access
* AWS CLI: Fully functional (certificate issues resolved)
* CloudFormation: Complete stack management capabilities
* Tagging: Use consistent tags for governance

## Technical Details
### Error Messages You Might See
#### SCP Denial (Expected for IGW/NAT):

UnauthorizedOperation: You are not authorized to perform this operation... 
with an explicit deny in a service control policy
### SSL Issues (Resolved in Devcontainer):

SSL validation failed... certificate verify failed: self signed certificate
Fix: export AWS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

### Route Table Configuration
Private subnets route: - 10.71.64.0/24 → local (VPC traffic) - 0.0.0.0/0 → tgw-0368e0eab67d69402 (Internet via Transit Gateway) - pl-7da54014 → vpce-066ce0c2c7f5d4a55 (AWS services via VPC Endpoint)

## Troubleshooting
### No Internet Access
1. Check security group outbound rules
1. Verify instance in private subnet (not isolated)
1. Check NACLs for subnet restrictions
1. Contact cloud team for Transit Gateway issues
### SSL Certificate Issues (Outside Devcontainer)
export AWS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
### Need Different Networking
Contact cloud/network team for: - Public subnet requirements - Direct internet connectivity - Custom routing needs

## Architecture Benefits
* Security: Centralized internet access control
* Cost: Shared Transit Gateway vs individual NAT gateways
* Compliance: Complete audit trail for internet traffic
* Scale: Single gateway serves multiple VPCs/accounts


Key Takeaway: This is a fully functional AWS environment with enterprise networking patterns. Only Internet/NAT Gateway creation is restricted - everything else works normally.

Last Updated: 2025-08-15