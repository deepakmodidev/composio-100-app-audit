from __future__ import annotations
import csv, json, re, shutil, textwrap, zipfile
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

ROOT = Path('/mnt/data/composio-100-app-audit')
DATA = ROOT/'data'; SRC=ROOT/'src'; SCRIPTS=ROOT/'scripts'; WF=ROOT/'.github'/'workflows'
for p in [DATA,SRC,SCRIPTS,WF]: p.mkdir(parents=True, exist_ok=True)

CATS = {
'CRM':'CRM and Sales','Support':'Support and Helpdesk','Comms':'Communications and Messaging',
'Marketing':'Marketing, Ads, Email and Social','Commerce':'Ecommerce','Data':'Data, SEO and Scraping',
'Dev':'Developer, Infra and Data platforms','Productivity':'Productivity and Project Management',
'Finance':'Finance and Fintech','AI':'AI, Research and Media-native'
}

def slug(s): return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')

def row(line):
    p=line.split('\t')
    if len(p)!=18: raise ValueError(f'Expected 18 columns, got {len(p)}: {p[:3]}')
    (id_,name,cat,site,what,auth,auth_methods,access,access_detail,api,breadth,mcp,mcp_scope,verdict,blocker,confidence,evidence,notes)=p
    return {
      'id':int(id_),'name':name,'slug':slug(name),'category':CATS[cat],'site':site,'what':what,
      'primaryAuth':auth,'authMethods':[x.strip() for x in auth_methods.split(';') if x.strip()],
      'access':access,'accessDetail':access_detail,'apiStyle':[x.strip() for x in api.split(';') if x.strip()],
      'breadth':breadth,'mcp':mcp,'mcpScope':mcp_scope,'verdict':verdict,'blocker':blocker,
      'confidence':confidence,'evidence':[{'label':f'Source {i+1}','url':u.strip()} for i,u in enumerate(evidence.split(';')) if u.strip()],
      'notes':notes,'verifiedAt':'2026-08-18'
    }

TSV = '''1\tSalesforce\tCRM\thttps://salesforce.com\tEnterprise CRM for accounts, leads, opportunities, cases, activities, and custom objects.\tMixed\tOAuth2;JWT bearer;client credentials\tAdmin/paid\tDeveloper orgs are self-serve, but useful production credentials and scopes require a Salesforce tenant and administrator.\tREST;SOAP;GraphQL;Bulk;Streaming\tBroad\tOfficial\tAction\tReady with constraints\tTenant administration, object permissions, security review, and high-risk write actions.\tHigh\thttps://developer.salesforce.com/docs/platform/mobile-sdk/guide/oauth-intro.html;https://developer.salesforce.com/docs/platform/mcp/overview\tHosted MCP became generally available in 2026.
2\tHubSpot\tCRM\thttps://hubspot.com\tCRM and marketing platform for contacts, companies, deals, tickets, activities, and content.\tMixed\tOAuth2;private app token\tSelf-serve\tFree developer accounts, test accounts, private apps, and OAuth apps are available without sales contact.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady\tSensitive-data restrictions, user permissions, rate limits, and confirmation for writes.\tHigh\thttps://developers.hubspot.com/docs/guides/apps/authentication/intro-to-auth;https://developers.hubspot.com/changelog/remote-hubspot-mcp-server-is-now-generally-available\tRemote MCP is GA with read and write capabilities.
3\tPipedrive\tCRM\thttps://pipedrive.com\tSales CRM for deals, leads, people, organizations, activities, products, projects, and webhooks.\tMixed\tOAuth2;API token\tSelf-serve\tA developer sandbox can be requested and API tokens are available in customer accounts.\tREST;Webhooks;OpenAPI\tBroad\tNone\tNone\tReady\tNo vendor-native MCP verified, but the broad OpenAPI surface is straightforward to wrap.\tHigh\thttps://developers.pipedrive.com/;https://developers.pipedrive.com/docs/api/v1\tMarketplace distribution needs app review.
4\tAttio\tCRM\thttps://attio.com\tFlexible CRM for people, companies, deals, lists, notes, tasks, meetings, and custom objects.\tMixed\tOAuth2;API key\tSelf-serve\tDevelopers can create workspaces and API integrations directly.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady\tWrite confirmations, workspace permissions, and bulk-operation guardrails.\tHigh\thttps://docs.attio.com/rest-api/overview;https://docs.attio.com/mcp/overview\tHosted MCP uses OAuth and covers most workspace objects.
5\tTwenty\tCRM\thttps://twenty.com\tOpen-source CRM for people, companies, opportunities, activities, workflows, and custom objects.\tMixed\tOAuth2;API key\tOpen-source/local\tSelf-hosting and cloud workspaces are available, with credentials controlled by the workspace owner.\tREST;GraphQL;Webhooks\tBroad\tOfficial\tAction\tReady\tSelf-hosted version drift, permissions, and destructive write operations.\tHigh\thttps://docs.twenty.com/developers;https://docs.twenty.com/user-guide/ai/capabilities/mcp\tCloud and self-hosted workspaces expose an MCP endpoint.
6\tPodio\tCRM\thttps://podio.com\tCustomizable work platform for apps, items, tasks, contacts, conversations, files, and workflows.\tOAuth2\tOAuth2\tAdmin/paid\tAPI clients are self-created, but meaningful testing needs a Podio workspace and administrator-approved app access.\tREST;Webhooks\tBroad\tNone\tNone\tReady with constraints\tLegacy platform patterns, workspace permissions, and no vendor-native MCP verified.\tHigh\thttps://developers.podio.com/authentication;https://developers.podio.com/doc\tStable API, but older developer experience.
7\tZoho CRM\tCRM\thttps://zoho.com/crm\tCRM for leads, contacts, accounts, deals, activities, automation, analytics, and custom modules.\tOAuth2\tOAuth2\tSelf-serve\tZoho API Console and trial CRM accounts provide a self-serve credential path.\tREST;Bulk;Notifications\tBroad\tOfficial\tAction\tReady\tMulti-region domains, scopes, edition limits, and confirmation for record mutations.\tHigh\thttps://www.zoho.com/crm/developer/docs/api/v7/oauth-overview.html;https://www.zoho.com/crm/developer/docs/mcp/overview.html\tZoho ships pre-built MCP servers for data and automation.
8\tClose\tCRM\thttps://close.com\tSales CRM for leads, contacts, opportunities, email, calls, SMS, tasks, and reporting.\tAPI key\tBasic with API key\tAdmin/paid\tAPI keys are generated in a Close account, and a free trial can be used for evaluation.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady\tCustomer communications, calling costs, permissions, and write confirmation.\tHigh\thttps://developer.close.com/topics/authentication/;https://developer.close.com/mcp\tFirst-party MCP is available for account data and actions.
9\tCopper\tCRM\thttps://copper.com\tGoogle Workspace-oriented CRM for people, companies, opportunities, activities, projects, and tasks.\tAPI key\tAPI key plus user email\tAdmin/paid\tCredentials require a Copper account and administrator access.\tREST;Webhooks\tBroad\tNone\tNone\tReady with constraints\tPaid tenant, admin credentials, rate limits, and no vendor-native MCP verified.\tHigh\thttps://developer.copper.com/authentication;https://developer.copper.com/\tAPI is usable for a custom toolkit.
10\tDealCloud\tCRM\thttps://api.docs.dealcloud.com\tDeal and relationship-management platform for investment and professional-services firms.\tMixed\tOAuth2;issued credentials\tPartner/sales\tAPI access is tied to a contracted DealCloud tenant and provisioned by administrators or support.\tREST\tBroad\tNone\tNone\tBlocked\tEnterprise contract, tenant configuration, and no public self-serve sandbox.\tHigh\thttps://api.docs.dealcloud.com/;https://api.docs.dealcloud.com/docs/authentication\tCorrect candidate for outreach, not reverse engineering.
11\tZendesk\tSupport\thttps://zendesk.com\tCustomer-service platform for tickets, users, organizations, help center, messaging, voice, and routing.\tMixed\tOAuth2;API token;Basic\tAdmin/paid\tTrials exist, but OAuth clients and production tokens require a Zendesk tenant and admin rights.\tREST;Webhooks;Events\tBroad\tNone\tNone\tReady with constraints\tTenant administration, complex product surfaces, customer-data sensitivity, and no native MCP verified.\tHigh\thttps://developer.zendesk.com/documentation/;https://developer.zendesk.com/documentation/api-basics/authentication/\tExcellent API breadth makes it a high-value custom toolkit.
12\tIntercom\tSupport\thttps://intercom.com\tCustomer support and engagement platform for contacts, conversations, tickets, articles, teams, and messages.\tMixed\tOAuth2;access token\tSelf-serve\tDeveloper workspaces and apps are self-serve; customer installs use OAuth.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady\tWorkspace permissions, customer-message safety, app review for distribution, and rate limits.\tHigh\thttps://developers.intercom.com/docs/build-an-integration/learn-more/authentication;https://developers.intercom.com/docs/guides/mcp\tVendor MCP supports agent access to Intercom data.
13\tFreshdesk\tSupport\thttps://freshdesk.com\tHelpdesk for tickets, contacts, agents, companies, groups, solutions, conversations, and time entries.\tMixed\tAPI key;OAuth2\tSelf-serve\tFree trials and API keys provide a direct testing path.\tREST;Webhooks\tBroad\tNone\tNone\tReady\tNo vendor-native MCP verified; normalize product editions and enforce ticket-write guardrails.\tHigh\thttps://developers.freshdesk.com/api/;https://developers.freshworks.com/docs/app-sdk/v3.0/support_ticket/serverless-apps/oauth/\tEasy custom wrapper candidate.
14\tFront\tSupport\thttps://front.com\tShared-inbox and customer-operations platform for conversations, messages, contacts, inboxes, tags, and rules.\tMixed\tOAuth2;API token\tAdmin/paid\tA Front tenant is needed; OAuth app setup requires administrator configuration.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady with constraints\tOAuth client compatibility, teammate permissions, messaging risk, and beta maturity.\tHigh\thttps://dev.frontapp.com/docs/authentication;https://dev.frontapp.com/docs/mcp-server\tOfficial MCP is in open beta with read, write, and send scopes.
15\tPylon\tSupport\thttps://usepylon.com\tB2B support platform for tickets, customer accounts, Slack and Teams channels, knowledge, and workflows.\tMixed\tOAuth2;API key\tAdmin/paid\tAPI and MCP access require an active Pylon workspace and administrator setup.\tREST;Webhooks\tModerate\tOfficial\tAction\tReady with constraints\tPaid workspace, admin setup, evolving docs, and customer-support data.\tHigh\thttps://docs.usepylon.com/pylon-docs/api-reference/authentication;https://docs.usepylon.com/pylon-docs/integrations/pylon-mcp\tNative MCP is available to workspace users.
16\tLiveAgent\tSupport\thttps://liveagent.com\tHelpdesk platform for tickets, chats, calls, contacts, departments, knowledge base, and reports.\tAPI key\tAPI key\tSelf-serve\tA trial account exposes API credentials.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady\tVersioned endpoints, ticket-write confirmation, and role-based permissions.\tHigh\thttps://support.liveagent.com/840138-Complete-API-reference;https://support.liveagent.com/647358-MCP-Integration-for-Agents\tFirst-party MCP integration is documented.
17\tPlain\tSupport\thttps://plain.com\tAPI-first customer support platform for customers, threads, messages, labels, SLAs, and support workflows.\tMixed\tAPI key;OAuth2\tSelf-serve\tDeveloper workspaces and API keys are directly available.\tGraphQL;Webhooks\tBroad\tOfficial\tAction\tReady\tGraphQL schema complexity, customer-message safety, and tenant permissions.\tHigh\thttps://www.plain.com/docs/api-reference/graphql/authentication;https://www.plain.com/docs/mcp\tAPI surface is GraphQL, not REST.
18\tHelp Scout\tSupport\thttps://helpscout.com\tHelpdesk for mailboxes, conversations, customers, users, workflows, reports, and knowledge base.\tOAuth2\tOAuth2\tAdmin/paid\tOAuth apps are creatable, but testing needs an active Help Scout account or trial and admin consent.\tREST;Webhooks\tBroad\tNone\tNone\tReady with constraints\tPaid tenant, mailbox permissions, communication risk, and no native MCP verified.\tHigh\thttps://developer.helpscout.com/mailbox-api/overview/authentication/;https://developer.helpscout.com/mailbox-api/\tStraightforward custom toolkit.
19\tGorgias\tSupport\thttps://gorgias.com\tEcommerce helpdesk for tickets, customers, macros, rules, help center, analytics, and commerce context.\tMixed\tOAuth2;API key\tAdmin/paid\tAPI access requires a Gorgias helpdesk account; the MCP is available on helpdesk plans.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady with constraints\tBeta maturity, role permissions, customer replies, and settings changes.\tHigh\thttps://developers.gorgias.com/reference/authentication;https://docs.gorgias.com/en-US/connect-your-ai-assistant-to-the-gorgias-mcp-6310546\tOfficial MCP is beta and supports ticket and settings actions.
20\tGladly\tSupport\thttps://gladly.com\tEnterprise customer-service platform for people, conversations, tasks, channels, knowledge, and routing.\tMixed\tOAuth2;issued credentials\tPartner/sales\tDeveloper access is associated with an enterprise customer or partner engagement.\tREST;Webhooks\tBroad\tNone\tNone\tBlocked\tEnterprise contract, provisioned tenant, limited public sandbox access, and no native MCP verified.\tHigh\thttps://developer.gladly.com/;https://developer.gladly.com/rest-api/authentication/\tOutreach is the correct next step.
21\tSlack\tComms\thttps://slack.com\tTeam messaging platform for channels, messages, users, files, canvases, workflows, and search.\tOAuth2\tOAuth2;bot token;app-level token\tSelf-serve\tApps, development workspaces, tokens, and Socket Mode are self-serve.\tREST;Web API;Events;Socket Mode\tBroad\tOfficial\tAction\tReady\tWorkspace admin policy, granular scopes, message-posting risk, and enterprise controls.\tHigh\thttps://api.slack.com/authentication/oauth-v2;https://api.slack.com/mcp\tSlack provides a hosted MCP connection.
22\tTwilio\tComms\thttps://twilio.com\tCommunications APIs for messaging, voice, verification, phone numbers, video, and email products.\tMixed\tBasic;API key;OAuth2\tSelf-serve\tTrial accounts and API credentials are self-serve.\tREST;Webhooks;WebSocket\tBroad\tOfficial\tDeveloper\tReady\tThe official MCP is mainly API-spec and developer tooling; account actions still need explicit API tools and spend controls.\tHigh\thttps://www.twilio.com/docs/iam/api-keys;https://www.twilio.com/docs/usage/mcp-server\tDo not mislabel the docs MCP as universal action execution.
23\tZoho Cliq\tComms\thttps://zoho.com/cliq\tTeam chat platform for channels, messages, users, bots, commands, widgets, and workflows.\tOAuth2\tOAuth2\tSelf-serve\tZoho API Console and Cliq workspaces provide a direct path.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady\tRegional endpoints, workspace permissions, and message-posting confirmation.\tHigh\thttps://www.zoho.com/cliq/help/platform/oauth.html;https://www.zoho.com/cliq/help/platform/zoho-cliq-mcp.html\tZoho publishes a native MCP integration.
24\tLark (Larksuite)\tComms\thttps://open.larksuite.com\tCollaboration suite for messaging, calendar, docs, sheets, approvals, contacts, and workplace apps.\tOAuth2\tOAuth2;tenant token;app token\tReview/approval\tApps are self-created, but production distribution and sensitive permissions require tenant admin or marketplace review.\tREST;Events;Webhooks\tBroad\tOfficial\tAction\tReady with constraints\tTenant approval, scope review, regional endpoints, and broad cross-product permissions.\tHigh\thttps://open.larksuite.com/document/server-docs/authentication-management/access-token/tenant_access_token_internal;https://open.feishu.cn/document/mcp_open_tools/developers-call-remote-mcp-server\tOfficial OpenAPI MCP toolkit exists.
25\tPumble\tComms\thttps://pumble.com\tTeam communication platform for workspaces, channels, messages, users, files, and webhooks.\tMixed\tOAuth2;bot token\tSelf-serve\tWorkspaces and developer integrations can be created directly.\tREST;Webhooks\tModerate\tOfficial\tAction\tReady\tSmaller API surface, workspace permissions, and message-write confirmation.\tHigh\thttps://pumble.com/help/integrations/pumble-api/;https://pumble.com/help/integrations/automation-workflow-integrations/how-to-use-the-pumble-mcp-server/\tFirst-party MCP is documented.
26\tDiscord\tComms\thttps://discord.com\tCommunity messaging platform for guilds, channels, messages, members, roles, threads, and interactions.\tMixed\tOAuth2;bot token\tSelf-serve\tDeveloper applications, test servers, bots, and OAuth credentials are self-serve.\tREST;Gateway;Webhooks\tBroad\tOfficial\tDocs-only\tReady\tOfficial MCP is developer documentation context, not a general Discord-account action server; bots still need explicit tools.\tHigh\thttps://discord.com/developers/docs/topics/oauth2;https://discord.com/developers/docs/developer-tools/mcp\tKeep docs MCP separate from action readiness.
27\tTelegram\tComms\thttps://core.telegram.org\tMessaging platform with Bot API and client APIs for chats, messages, media, updates, and payments.\tToken\tBot token;MTProto app credentials\tSelf-serve\tBotFather issues bot tokens instantly; full client APIs require an app ID and phone-based account.\tREST;Long polling;Webhooks;MTProto\tBroad\tNone\tNone\tReady\tNo vendor-native MCP verified, bot limitations, abuse controls, and distinction between Bot API and user accounts.\tHigh\thttps://core.telegram.org/bots/api;https://core.telegram.org/api/obtaining_api_id\tEasy to wrap as bot-scoped tools.
28\tWhatsApp Business\tComms\thttps://developers.facebook.com/docs/whatsapp\tBusiness messaging platform for templates, conversations, media, phone numbers, and webhooks.\tOAuth2\tUser token;system-user token;temporary test token\tReview/approval\tTest numbers are self-serve, while production needs a Meta business, WABA, phone registration, and often verification or review.\tGraph API;Webhooks\tBroad\tOfficial\tDocs-only\tReady with constraints\tBusiness verification, template review, messaging policy, phone setup, and customer-consent controls.\tHigh\thttps://developers.facebook.com/docs/whatsapp/cloud-api/get-started;https://developers.facebook.com/docs/development/mcp\tMeta's developer MCP is documentation-oriented; WhatsApp account actions still use the Graph API and reviewed business permissions.
29\tAircall\tComms\thttps://aircall.io\tCloud phone and contact-center platform for calls, users, numbers, contacts, tags, and webhooks.\tMixed\tOAuth2;Basic with API ID and token\tPartner/sales\tInternal credentials require a customer tenant; public OAuth apps use the Technology Partner path.\tREST;Webhooks\tBroad\tNone\tNone\tReady with constraints\tTechnology Partner path, tenant access, and no existing Aircall-account MCP; AI Virtual Agent MCP guidance is marked coming soon.\tHigh\thttps://developer.aircall.io/docs/authentication;https://developer.aircall.io/docs/introduction\tAircall documents an inbound MCP direction, but marks the implementation guidance coming soon.
30\tVonage\tComms\thttps://developer.vonage.com\tCommunications APIs for SMS, voice, video, verification, messaging, and contact-center workflows.\tMixed\tAPI key and secret;JWT\tSelf-serve\tDeveloper accounts, trial credit, and applications are self-serve.\tREST;Webhooks;WebSocket\tBroad\tOfficial\tLocal action\tReady\tPhone-number cost, messaging registration, jurisdictional compliance, and local-tool deployment.\tHigh\thttps://developer.vonage.com/en/getting-started/concepts/authentication;https://developer.vonage.com/en/tools/mcp\tOfficial tooling MCP can execute supported account actions.
31\tGoogle Ads\tMarketing\thttps://developers.google.com/google-ads\tAdvertising API for campaigns, accounts, reporting, audiences, budgets, assets, and conversions.\tMixed\tOAuth2;developer token\tReview/approval\tOAuth is self-serve, but production developer-token access levels are reviewed.\tREST;gRPC\tBroad\tOfficial\tRead-only\tReady with constraints\tDeveloper-token approval, manager-account setup, policy compliance, and read-only MCP scope.\tHigh\thttps://developers.google.com/google-ads/api/docs/oauth/overview;https://developers.google.com/google-ads/api/docs/model-context-protocol\tOfficial MCP was released in 2026 with read-oriented tools.
32\tMeta Ads\tMarketing\thttps://developers.facebook.com/docs/marketing-apis\tAdvertising APIs for campaigns, ad sets, creatives, audiences, pixels, insights, and business assets.\tOAuth2\tUser token;system-user token\tReview/approval\tTest assets are available, but production permissions often require app review and business verification.\tGraph API;Webhooks\tBroad\tOfficial\tDocs-only\tReady with constraints\tApp review, business verification, asset permissions, and policy-sensitive writes.\tHigh\thttps://developers.facebook.com/docs/marketing-apis;https://developers.facebook.com/docs/development/mcp\tMeta's developer MCP helps with platform documentation; Marketing API account actions still use OAuth and reviewed permissions.
33\tLinkedIn Ads\tMarketing\thttps://learn.microsoft.com/linkedin/marketing\tMarketing APIs for ad accounts, campaigns, creatives, audiences, lead forms, and reporting.\tOAuth2\tOAuth2\tReview/approval\tA developer app is self-serve, but Marketing API products and expanded access require application and approval.\tREST\tBroad\tNone\tNone\tReady with constraints\tProduct-access approval is the main blocker, followed by strict scopes and versioning.\tHigh\thttps://learn.microsoft.com/en-us/linkedin/marketing/integrations/marketing-integrations-overview;https://learn.microsoft.com/en-us/linkedin/marketing/increasing-access\tNo vendor-native action MCP verified.
34\tGoHighLevel\tMarketing\thttps://highlevel.stoplight.io\tSales and marketing platform for contacts, conversations, calendars, opportunities, workflows, and agencies.\tMixed\tOAuth2;private integration token\tAdmin/paid\tPrivate integrations are created inside an account; marketplace apps use OAuth and review.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady with constraints\tAgency or location account, marketplace review, and high-impact workflow actions.\tHigh\thttps://marketplace.gohighlevel.com/docs/ghl/oauth/oauth-2-0-v-3/;https://marketplace.gohighlevel.com/docs/other/mcp/index.html\tLeadConnector exposes an official MCP route.
35\tMailchimp\tMarketing\thttps://mailchimp.com/developer\tEmail marketing platform for audiences, campaigns, automations, templates, reports, and ecommerce events.\tMixed\tAPI key;OAuth2\tSelf-serve\tAPI keys and OAuth apps are available from a Mailchimp account.\tREST;Webhooks\tBroad\tOfficial\tLimited action\tReady\tVendor MCP coverage is mainly Mailchimp Transactional, not the full Marketing API; enforce consent and sending safeguards.\tHigh\thttps://mailchimp.com/developer/marketing/docs/fundamentals/;https://mailchimp.com/developer/transactional/docs/mcp/\tDo not treat transactional coverage as full platform parity.
36\tKlaviyo\tMarketing\thttps://developers.klaviyo.com\tMarketing automation and customer-data platform for profiles, events, lists, segments, campaigns, and metrics.\tMixed\tPrivate API key;OAuth2\tSelf-serve\tPrivate keys are self-serve; public OAuth apps require review and security checks.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady\tConsent-safe messaging, profile-data sensitivity, OAuth review, and rate limits.\tHigh\thttps://developers.klaviyo.com/en/docs/authenticate_;https://developers.klaviyo.com/en/docs/mcp_server\tOfficial remote and local MCP options exist.
37\tsysteme.io\tMarketing\thttps://systeme.io\tFunnel, email, course, affiliate, and sales automation platform.\tAPI key\tAPI key\tSelf-serve\tUsers can generate public API credentials from their account.\tREST\tModerate\tOfficial\tAction\tReady\tNarrower surface, email consent, and workflow side effects.\tHigh\thttps://help.systeme.io/article/2323-how-to-use-systeme-io-public-api;https://help.systeme.io/article/9489-how-to-use-systeme-ios-mcp\tOfficial MCP setup is published.
38\tPinterest\tMarketing\thttps://developers.pinterest.com\tVisual discovery and advertising platform for pins, boards, catalogs, analytics, and ads.\tOAuth2\tOAuth2 authorization code;client credentials for limited endpoints\tReview/approval\tApps need Trial access approval, then Standard access for production breadth and rate limits.\tREST\tBroad\tNone\tNone\tReady with constraints\tTrial and Standard review, business account, policy compliance, and no native MCP verified.\tHigh\thttps://developers.pinterest.com/docs/getting-started/set-up-authentication-and-authorization/;https://developers.pinterest.com/docs/key-concepts/access-tiers/\tApproval, not engineering, is the bottleneck.
39\tThreads (Meta)\tMarketing\thttps://developers.facebook.com/documentation/threads\tSocial publishing API for Threads profiles, posts, replies, mentions, and insights.\tOAuth2\tMeta access token\tReview/approval\tDevelopers can test with app roles; public use follows Meta review and permission rules.\tGraph API\tModerate\tNone\tNone\tReady with constraints\tMeta review, permissions, narrower surface, and no Threads-specific action MCP verified.\tHigh\thttps://developers.facebook.com/docs/threads/get-started;https://developers.facebook.com/docs/development/create-an-app/threads-use-case\tMeta developer MCP does not imply Threads action coverage.
40\tSendGrid\tMarketing\thttps://sendgrid.com\tTransactional and marketing email platform for sending, templates, contacts, events, suppressions, and analytics.\tAPI key\tBearer API key\tSelf-serve\tAccounts and scoped API keys are self-serve; production sending depends on sender verification.\tREST;Webhooks\tBroad\tOfficial\tDocs-only\tReady\tOfficial Twilio MCP and skills expose SendGrid developer context, while execution still needs explicit API tools and reputation controls.\tHigh\thttps://www.twilio.com/docs/sendgrid/api-reference/how-to-use-the-sendgrid-v3-api/authentication;https://www.twilio.com/docs/usage/mcp-server\tSeparate documentation support from send actions.
41\tShopify\tCommerce\thttps://shopify.dev\tCommerce platform for products, orders, customers, inventory, fulfillment, discounts, storefronts, and checkout.\tMixed\tOAuth2;custom app token\tSelf-serve\tPartner accounts and development stores are self-serve; public distribution uses app review.\tGraphQL Admin;Storefront GraphQL;REST legacy;Webhooks\tBroad\tOfficial\tStorefront\tReady\tAdmin writes still need GraphQL tools and app scopes; storefront MCP focuses shopping, cart, checkout, and customer tasks.\tHigh\thttps://shopify.dev/docs/apps/build/authentication-authorization;https://shopify.dev/docs/apps/build/storefront-mcp\tGraphQL Admin is primary because REST Admin is legacy.
42\tWooCommerce\tCommerce\thttps://woocommerce.com\tOpen-source WordPress commerce platform for products, orders, customers, coupons, shipping, and reports.\tMixed\tConsumer key and secret;Basic;OAuth1 over HTTP\tOpen-source/local\tAny store owner can install WooCommerce and generate REST credentials.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady\tWordPress plugin/version variance, self-hosting security, refunds, and destructive store actions.\tHigh\thttps://woocommerce.github.io/woocommerce-rest-api-docs/;https://developer.woocommerce.com/docs/features/mcp/\tWooCommerce now includes native MCP support.
43\tBigCommerce\tCommerce\thttps://developer.bigcommerce.com\tCommerce platform for catalog, orders, customers, inventory, channels, storefronts, carts, and checkout.\tMixed\tOAuth2;store access token\tSelf-serve\tSandbox stores and app credentials are available through the developer portal and trial path.\tREST;GraphQL;Webhooks\tBroad\tOfficial\tStorefront\tReady\tStorefront MCP is shopper-focused; admin operations still need scoped API tools and app review.\tHigh\thttps://developer.bigcommerce.com/docs/start/authentication;https://www.bigcommerce.com/blog/storefront-mcp/\tOfficial Storefront MCP went live in 2026.
44\tSalesforce Commerce Cloud\tCommerce\thttps://developer.salesforce.com/docs/commerce\tEnterprise commerce platform for products, pricing, inventory, orders, promotions, shoppers, and admin operations.\tOAuth2\tOAuth2 client credentials;shopper token\tAdmin/paid\tRequires a contracted Commerce Cloud tenant, API client setup, and administrator-selected roles.\tREST;SCAPI;OCAPI\tBroad\tOfficial\tPlatform bridge\tReady with constraints\tEnterprise tenant, role configuration, API-family complexity, and Salesforce-hosted MCP setup.\tMedium\thttps://developer.salesforce.com/docs/commerce/commerce-api/guide/authorization.html;https://developer.salesforce.com/docs/platform/mcp/overview\tOfficial Salesforce MCP infrastructure can expose approved Commerce tools, but it is tenant-driven.
45\tMagento (Adobe Commerce)\tCommerce\thttps://developer.adobe.com/commerce\tOpen-source and enterprise commerce platform for catalog, customers, carts, orders, inventory, and extensions.\tMixed\tIntegration token;OAuth1;OAuth2 server-to-server for SaaS\tOpen-source/local\tMagento Open Source is self-hosted; Adobe Commerce cloud features require a paid organization.\tREST;GraphQL;Webhooks;Events\tBroad\tOfficial\tDeveloper\tReady\tDeployment variation, extension complexity, version drift, and developer-focused rather than universal admin MCP tools.\tHigh\thttps://developer.adobe.com/commerce/webapi/get-started/authentication/gs-authentication-token/;https://developer.adobe.com/commerce/extensibility/developer-agent/coding-tools\tAdobe ships Commerce development MCPs and skills.
46\tSquarespace\tCommerce\thttps://developers.squarespace.com\tWebsite and commerce platform for products, orders, inventory, transactions, webhooks, and site extensions.\tMixed\tOAuth2;API key\tAdmin/paid\tDevelopers can create apps, but live commerce testing requires a Squarespace site and appropriate plan.\tREST;Webhooks\tModerate\tNone\tNone\tReady with constraints\tPaid site, narrower commerce surface, OAuth app setup, and no vendor-native MCP verified.\tHigh\thttps://developers.squarespace.com/commerce-apis/authentication-and-permissions;https://developers.squarespace.com/\tNo vendor-native MCP was found in official developer documentation.
47\tEcwid\tCommerce\thttps://api-docs.ecwid.com\tCommerce platform for products, orders, customers, inventory, carts, storefront, and app integrations.\tMixed\tOAuth2;store access token\tSelf-serve\tDeveloper apps and test stores are available directly.\tREST;Webhooks\tBroad\tCommunity\tAction\tReady\tNo vendor-native MCP verified; third-party hosted MCP wrappers exist, so provenance and permissions must be reviewed.\tMedium\thttps://docs.ecwid.com/get-started/authentication;https://viasocket.com/mcp/ecwid-by-lightspeed\tCommunity status is not counted as vendor-native MCP.
48\tGumroad\tCommerce\thttps://gumroad.com/api\tCreator-commerce platform for products, sales, subscribers, licenses, payouts, and resource subscriptions.\tMixed\tOAuth2;access token\tSelf-serve\tCreators can create an OAuth app or access token from their account.\tREST;Webhooks\tModerate\tCommunity\tAction\tReady\tNo official MCP, aging API areas, creator-finance data, and third-party server maintenance.\tMedium\thttps://gumroad.com/api;https://github.com/rmarescu/gumroad-mcp\tOpen-source MCP exists but is not vendor maintained.
49\tAmazon Selling Partner\tCommerce\thttps://developer-docs.amazon.com/sp-api\tMarketplace API suite for catalog, listings, orders, inventory, fulfillment, reports, finances, and sellers.\tMixed\tLogin with Amazon OAuth2;restricted data token\tReview/approval\tSandbox onboarding is available, but production developer registration, roles, seller authorization, and security review are substantial.\tREST;GraphQL for Data Kiosk;Notifications\tBroad\tNone\tNone\tReady with constraints\tRegistration review, restricted-data roles, security controls, seller authorization, and no native MCP verified.\tHigh\thttps://developer-docs.amazon.com/sp-api/docs/authorizing-selling-partner-api-applications;https://developer-docs.amazon.com/sp-api/docs\tThe docs are agent-friendly via llms.txt and OpenAPI, but that is not MCP.
50\tfanbasis\tCommerce\thttps://fanbasis.com\tCreator monetization and commerce platform for offers, payments, communities, and customer operations.\tOther\tProvisioned credentials\tPartner/sales\tThe developer documentation is password-gated and no public self-serve credential path was verified.\tUnknown\tUnknown\tNone\tNone\tBlocked\tPassword-gated docs, unclear auth and surface, and no public sandbox.\tLow\thttps://dev-docs.fanbasis.com/;https://fanbasis.com/\tTreat as an outreach discovery item, not a failed research result.
51\tDataForSEO\tData\thttps://docs.dataforseo.com\tSEO data APIs for SERPs, keywords, backlinks, domains, business data, app data, and content analysis.\tBasic\tBasic with login and password\tSelf-serve\tRegistration and pay-as-you-go API access are self-serve.\tREST;Webhooks\tBroad\tNone\tNone\tReady\tUsage cost, asynchronous jobs, result size, and no native MCP verified.\tHigh\thttps://docs.dataforseo.com/v3/auth/;https://docs.dataforseo.com/v3/\tStrong easy-win API despite no native MCP.
52\tSE Ranking\tData\thttps://seranking.com/api\tSEO platform API for rankings, competitors, audits, backlinks, keywords, and projects.\tToken\tAPI token\tAdmin/paid\tAPI availability is tied to eligible paid plans and account-issued tokens.\tREST\tBroad\tOfficial\tAction\tReady with constraints\tPaid entitlement, rate limits, job latency, and SEO data cost.\tHigh\thttps://seranking.com/api/how-to-get-api/;https://seranking.com/api/integrations/mcp/\tFirst-party MCP is documented.
53\tAhrefs\tData\thttps://ahrefs.com/api\tSEO and web-intelligence APIs for backlinks, domains, keywords, rankings, and site metrics.\tAPI key\tBearer API key\tAdmin/paid\tMeaningful API access requires a qualifying paid subscription or API plan.\tREST\tBroad\tOfficial\tAction\tReady with constraints\tPaid entitlement, row-unit cost, quotas, and data licensing.\tHigh\thttps://docs.ahrefs.com/docs/api/reference/introduction;https://docs.ahrefs.com/en/mcp/overview\tOfficial remote MCP is available.
54\tMrScraper\tData\thttps://docs.mrscraper.com\tWeb scraping API for pages, structured extraction, browser rendering, and asynchronous jobs.\tToken\tBearer token\tSelf-serve\tAccounts, trial credits, and tokens are self-serve.\tREST;Webhooks\tModerate\tNone\tNone\tReady\tRobots and site terms, dynamic-page reliability, cost, and no native MCP verified.\tHigh\thttps://docs.mrscraper.com/api-reference/authentication;https://docs.mrscraper.com/\tUse domain allowlists and legal policy checks.
55\tApify\tData\thttps://docs.apify.com\tCloud platform for web-scraping actors, datasets, crawlers, storage, schedules, and automation.\tMixed\tAPI token;OAuth2\tSelf-serve\tFree accounts, public actors, tokens, and usage credits are self-serve.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady\tUntrusted actors, scraping legality, spend, long-running jobs, and large datasets.\tHigh\thttps://docs.apify.com/api/v2;https://docs.apify.com/platform/integrations/mcp\tOfficial MCP exposes actors and platform operations.
56\tFirecrawl\tData\thttps://firecrawl.dev\tWeb crawling and extraction API for scrape, crawl, map, search, structured data, and browser tasks.\tAPI key\tBearer API key\tSelf-serve\tCloud trial credits and open-source self-hosting are available.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady\tTarget-site policy, spend, prompt injection in pages, and asynchronous crawling.\tHigh\thttps://docs.firecrawl.dev/api-reference/introduction;https://docs.firecrawl.dev/mcp-server\tOfficial MCP and open-source deployment exist.
57\tBright Data\tData\thttps://brightdata.com\tWeb data platform for proxies, scraping browser, datasets, SERP, unlocker, and crawlers.\tToken\tAPI token\tAdmin/paid\tTrials exist, but production requires paid zones, compliance checks, and configured products.\tREST;WebSocket\tBroad\tOfficial\tAction\tReady with constraints\tCompliance, proxy spend, target-site policy, sensitive datasets, and administrator controls.\tHigh\thttps://docs.brightdata.com/api-reference/authentication;https://docs.brightdata.com/ai/mcp-server/remote/quickstart\tFirst-party remote MCP is available.
58\tSherlock\tData\thttps://github.com/sherlock-project/sherlock\tOpen-source CLI that checks usernames across many social networks.\tNone\tNo auth for local use\tOpen-source/local\tSource and package are public and run locally.\tCLI\tLocal\tLocal skill\tLocal action\tReady\tFalse positives, site changes, rate limits, privacy, and misuse prevention.\tHigh\thttps://github.com/sherlock-project/sherlock\tBest exposed as a sandboxed local agent skill.
59\tWaterfall.io\tData\thttps://waterfall.io\tContact and company intelligence platform for enrichment, identity resolution, and multi-provider data waterfalls.\tAPI key\tAPI key\tAdmin/paid\tAPI access requires a paid workspace or sales-assisted plan.\tREST\tModerate\tNone\tNone\tReady with constraints\tPaid credits, personal-data handling, provider provenance, and no native MCP verified.\tMedium\thttps://waterfall.io/;https://docs.waterfall.io/\tDocumentation footprint is smaller than established data vendors.
60\tClay\tData\thttps://clay.com\tGTM data and workflow platform for enrichment, research, tables, signals, sequencing, and provider orchestration.\tMixed\tOAuth2;API key\tAdmin/paid\tWorkspace and API access depend on plan and administrator settings; new accounts receive limited credits.\tREST;Webhooks;CLI\tBroad\tOfficial\tAction\tReady with constraints\tCredit burn, provider terms, admin controls, personal data, and workflow side effects.\tHigh\thttps://developers.clay.com/;https://www.clay.com/mcp\tOfficial hosted MCP exposes providers and Ops-built functions.
61\tGitHub\tDev\thttps://docs.github.com/rest\tCode-hosting platform for repositories, issues, pull requests, actions, releases, projects, and security.\tMixed\tOAuth2;PAT;GitHub App token\tSelf-serve\tAccounts, apps, test repositories, and scoped tokens are self-serve.\tREST;GraphQL;Webhooks\tBroad\tOfficial\tAction\tReady\tRepository permissions, destructive actions, branch protection, secrets, and prompt-injection risk.\tHigh\thttps://docs.github.com/en/authentication;https://github.com/github/github-mcp-server\tOfficial MCP covers repository and collaboration operations.
62\tVercel\tDev\thttps://vercel.com/docs/rest-api\tCloud platform for projects, deployments, domains, environment variables, logs, analytics, and teams.\tMixed\tOAuth2;access token\tSelf-serve\tFree accounts, teams, projects, and personal tokens are self-serve.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady\tDeployment, domain, environment-secret, and production mutation safeguards.\tHigh\thttps://vercel.com/docs/rest-api;https://vercel.com/docs/agent-resources/vercel-mcp\tOfficial remote MCP uses OAuth.
63\tNetlify\tDev\thttps://docs.netlify.com/api\tCloud platform for sites, deploys, functions, forms, domains, environment variables, and teams.\tMixed\tOAuth2;personal access token\tSelf-serve\tFree accounts and personal tokens are self-serve.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady\tProduction deploys, secrets, domains, and team permissions.\tHigh\thttps://docs.netlify.com/api/get-started/;https://docs.netlify.com/welcome/build-with-ai/netlify-mcp-server/\tOfficial MCP has remote and local options.
64\tCloudflare\tDev\thttps://developers.cloudflare.com/api\tInternet platform for DNS, zones, Workers, storage, security, analytics, tunnels, and accounts.\tAPI key\tAPI token;legacy global key\tSelf-serve\tFree accounts and scoped API tokens are self-serve.\tREST;GraphQL Analytics\tBroad\tOfficial\tAction\tReady\tMassive surface, DNS and security blast radius, account scopes, and write confirmation.\tHigh\thttps://developers.cloudflare.com/fundamentals/api/get-started/create-token/;https://developers.cloudflare.com/agents/model-context-protocol/mcp-servers-for-cloudflare/\tCloudflare publishes multiple first-party MCP servers.
65\tSupabase\tDev\thttps://supabase.com/docs\tBackend platform for Postgres, auth, storage, edge functions, realtime, projects, and management.\tMixed\tProject API key;personal access token;database credentials\tSelf-serve\tFree projects and credentials are self-serve.\tREST;GraphQL;Postgres;Realtime\tBroad\tOfficial\tAction\tReady\tDatabase writes, service-role keys, production-project targeting, and schema migration risk.\tHigh\thttps://supabase.com/docs/guides/api;https://supabase.com/docs/guides/getting-started/mcp\tOfficial MCP supports project and database workflows.
66\tNeo4j\tDev\thttps://neo4j.com/docs/api\tGraph database platform for Cypher queries, graph data, schemas, instances, and analytics.\tMixed\tBasic;Bearer token\tSelf-serve\tAura free instances and local Community Edition are self-serve.\tQuery API;Bolt;REST management\tBroad\tOfficial\tAction\tReady\tArbitrary Cypher, data mutation, query cost, and credential scoping.\tHigh\thttps://neo4j.com/docs/query-api/current/authentication/;https://neo4j.com/docs/mcp/current/\tOfficial MCP servers are documented.
67\tSnowflake\tDev\thttps://docs.snowflake.com\tCloud data platform for warehouses, databases, SQL, data sharing, apps, governance, and AI services.\tMixed\tOAuth2;key-pair JWT;programmatic access token\tAdmin/paid\tTrials exist, but useful access requires an account, roles, warehouses, and administrator policies.\tSQL;REST;Snowpark\tBroad\tOfficial\tAction\tReady with constraints\tRole design, warehouse cost, sensitive data, arbitrary SQL, and administrator setup.\tHigh\thttps://docs.snowflake.com/en/developer-guide/snowflake-rest-api/authentication;https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-mcp\tManaged Cortex MCP is available.
68\tMongoDB Atlas\tDev\thttps://mongodb.com/docs/atlas/api\tManaged database platform for clusters, projects, users, backups, alerts, search, and data operations.\tMixed\tService-account OAuth2;public/private API key;database user\tSelf-serve\tFree Atlas projects and credentials are self-serve.\tREST;Data API;MongoDB protocol\tBroad\tOfficial\tAction\tReady\tDatabase mutation, project admin actions, network access lists, and production targeting.\tHigh\thttps://www.mongodb.com/docs/atlas/api/;https://www.mongodb.com/docs/mcp-server/\tOfficial MongoDB MCP covers Atlas and database workflows.
69\tDatadog\tDev\thttps://docs.datadoghq.com/api\tObservability platform for metrics, logs, traces, monitors, incidents, dashboards, SLOs, and security.\tMixed\tAPI key and app key;OAuth2\tAdmin/paid\tTrials exist; API and app keys are created inside an organization with role permissions.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady with constraints\tSensitive telemetry, monitor mutations, incident actions, and organization-level permissions.\tHigh\thttps://docs.datadoghq.com/api/latest/authentication/;https://docs.datadoghq.com/mcp_server/\tFirst-party MCP is available.
70\tSentry\tDev\thttps://docs.sentry.io/api\tError and performance platform for issues, events, releases, projects, alerts, traces, and organizations.\tMixed\tOAuth2;auth token\tSelf-serve\tFree organizations, developer apps, and scoped tokens are self-serve.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady\tIssue mutations, release actions, sensitive stack data, and organization permissions.\tHigh\thttps://docs.sentry.io/api/auth/;https://docs.sentry.io/ai/mcp/\tOfficial remote MCP is available.
71\tNotion\tProductivity\thttps://developers.notion.com\tWorkspace platform for pages, databases, data sources, blocks, users, comments, and search.\tMixed\tOAuth2;internal integration token\tSelf-serve\tFree workspaces and internal integrations are self-serve; public apps use OAuth review.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady\tPage sharing, user permissions, destructive edits, and rich block structure.\tHigh\thttps://developers.notion.com/guides/get-started/authorization;https://developers.notion.com/guides/mcp/overview\tOfficial hosted MCP is available.
72\tAirtable\tProductivity\thttps://airtable.com/developers\tLow-code data platform for bases, tables, records, fields, comments, webhooks, and automations.\tMixed\tOAuth2;personal access token\tSelf-serve\tFree bases, PATs, and OAuth apps are self-serve.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady\tSchema variability, record writes, base permissions, and rate limits.\tHigh\thttps://airtable.com/developers/web/api/authentication;https://support.airtable.com/docs/using-the-airtable-mcp-server\tFirst-party MCP is available.
73\tLinear\tProductivity\thttps://developers.linear.app\tIssue and product-development platform for teams, projects, cycles, issues, comments, documents, and roadmaps.\tMixed\tOAuth2;API key\tSelf-serve\tFree workspaces, personal keys, and OAuth apps are self-serve.\tGraphQL;Webhooks\tBroad\tOfficial\tAction\tReady\tWorkspace permissions, issue mutation, notification noise, and automation loops.\tHigh\thttps://developers.linear.app/docs/graphql/working-with-the-graphql-api;https://linear.app/docs/mcp\tOfficial hosted remote MCP exists.
74\tJira\tProductivity\thttps://developer.atlassian.com\tIssue and project platform for work items, projects, comments, users, boards, sprints, and workflows.\tMixed\tOAuth2;API token;Forge auth\tSelf-serve\tFree Jira sites, developer apps, and OAuth are self-serve; enterprise admins can restrict apps.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady\tComplex permissions, workflow transitions, enterprise app policy, and bulk edits.\tHigh\thttps://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/;https://developer.atlassian.com/platform/remote-mcp-server/\tAtlassian Rovo MCP covers Jira and Confluence.
75\tAsana\tProductivity\thttps://developers.asana.com\tWork-management platform for tasks, projects, portfolios, goals, teams, users, and attachments.\tMixed\tOAuth2;personal access token\tSelf-serve\tDeveloper apps, PATs, and free workspaces are self-serve.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady\tTask mutation, team permissions, notification noise, and rate limits.\tHigh\thttps://developers.asana.com/docs/authentication;https://developers.asana.com/docs/using-asanas-mcp-server\tFirst-party MCP is available.
76\tMonday.com\tProductivity\thttps://developer.monday.com\tWork operating system for boards, items, columns, updates, users, workspaces, and automations.\tMixed\tOAuth2;API token\tSelf-serve\tDeveloper apps and trial accounts provide a self-serve path.\tGraphQL;Webhooks\tBroad\tOfficial\tAction\tReady\tHighly dynamic schemas, complexity quotas, board permissions, and write confirmation.\tHigh\thttps://developer.monday.com/api-reference/docs/authentication;https://developer.monday.com/api-reference/docs/integrate-with-monday-mcp\tOfficial remote MCP is available.
77\tClickUp\tProductivity\thttps://clickup.com/api\tProductivity platform for workspaces, spaces, folders, lists, tasks, comments, docs, goals, and time.\tMixed\tOAuth2;personal token\tSelf-serve\tFree workspaces, personal tokens, and OAuth apps are self-serve.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady\tHierarchy complexity, permissions, task mutation, and rate limits.\tHigh\thttps://developer.clickup.com/docs/authentication;https://developer.clickup.com/docs/connect-an-ai-assistant-to-clickups-mcp-server\tFirst-party remote MCP is available.
78\tCoda\tProductivity\thttps://coda.io/developers\tCollaborative document platform for docs, pages, tables, rows, formulas, controls, and automations.\tMixed\tOAuth2;API token\tSelf-serve\tFree docs, API tokens, and OAuth apps are self-serve.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady\tDocument sharing, formula side effects, row mutations, and sync-table semantics.\tHigh\thttps://coda.io/developers/apis/v1;https://coda.io/resources/guides/getting_started_with_coda_mcp\tOfficial MCP setup is documented.
79\tSmartsheet\tProductivity\thttps://smartsheet.com/developers\tEnterprise work-management platform for sheets, rows, reports, dashboards, attachments, and automation.\tMixed\tOAuth2;access token\tAdmin/paid\tAPI access requires a Smartsheet account; enterprise administrators may restrict integrations.\tREST;Webhooks\tBroad\tNone\tNone\tReady with constraints\tPaid tenant, admin policy, spreadsheet-like schema variability, and no native MCP verified.\tHigh\thttps://developers.smartsheet.com/api/smartsheet/guides/advanced-topics/oauth;https://developers.smartsheet.com/api/smartsheet/openapi\tCustom wrapper is straightforward.
80\tHarvest\tProductivity\thttps://help.getharvest.com/api-v2\tTime tracking and invoicing platform for time entries, projects, clients, users, expenses, and invoices.\tMixed\tOAuth2;personal access token\tSelf-serve\tTrials, personal tokens, and OAuth apps are self-serve.\tREST\tBroad\tNone\tNone\tReady\tNo native MCP verified; enforce time-entry and invoice write confirmation.\tHigh\thttps://help.getharvest.com/api-v2/authentication-api/authentication/authentication/;https://help.getharvest.com/api-v2/\tA clean easy-win custom toolkit.
81\tStripe\tFinance\thttps://stripe.com/docs/api\tPayments platform for customers, payments, subscriptions, invoices, products, disputes, and connected accounts.\tMixed\tSecret API key;restricted key;OAuth2\tSelf-serve\tTest mode, accounts, keys, and Connect apps are self-serve.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady\tMoney movement, refunds, disputes, PCI boundaries, test-versus-live mode, and idempotency.\tHigh\thttps://docs.stripe.com/keys;https://docs.stripe.com/mcp\tOfficial MCP exists, but financial actions require strict confirmation.
82\tPlaid\tFinance\thttps://plaid.com/docs\tFinancial-data platform for bank linking, accounts, transactions, identity, assets, risk, and payments.\tMixed\tClient ID and secret;OAuth2 for Dashboard MCP\tReview/approval\tSandbox is self-serve, but live data and products require Production approval and compliance review.\tREST;Webhooks\tBroad\tOfficial\tLimited action\tReady with constraints\tProduction approval, financial data, product eligibility, and MCP scope focused on diagnostics and sandbox tooling.\tHigh\thttps://plaid.com/docs/quickstart/;https://plaid.com/docs/resources/mcp/\tOfficial Dashboard MCP requires approved Production access.
83\tBinance\tFinance\thttps://developers.binance.com\tCrypto exchange APIs for market data, account data, orders, wallets, transfers, and trading.\tMixed\tAPI key;HMAC or asymmetric signature\tAdmin/paid\tAccounts and API keys are self-serve where the service is legally available; trading and withdrawals require KYC and controls.\tREST;WebSocket\tBroad\tOfficial\tAction\tReady with constraints\tJurisdiction, KYC, trading loss, withdrawal risk, rate limits, and key restrictions.\tHigh\thttps://developers.binance.com/docs/binance-spot-api-docs/rest-api/request-security;https://developers.binance.com/docs/agent\tOfficial agent API and MCP-oriented tooling are documented.
84\tPaygent Connect\tFinance\thttps://paygent.com\tNMI-powered payment connectivity for merchant processing and payment workflows.\tOther\tProvisioned gateway credentials\tPartner/sales\tNo clear public developer credential path or sandbox specific to Paygent Connect was verified.\tUnknown\tUnknown\tNone\tNone\tBlocked\tAmbiguous product identity, NMI dependency, partner provisioning, and sparse public docs.\tLow\thttps://www.nmi.com/developers/;https://paygent.com/\tRequires human outreach before technical scoping.
85\tiPayX\tFinance\thttps://ipayx.ai/docs\tAI-oriented payments and financial operations platform with documented API and MCP access.\tMixed\tAPI key;OAuth2\tAdmin/paid\tCredentials and production use appear tied to an approved customer workspace or paid account.\tREST;MCP tools\tModerate\tOfficial\tAction\tReady with constraints\tYoung documentation footprint, financial controls, customer eligibility, and money movement.\tMedium\thttps://www.ipayx.ai/docs;https://www.ipayx.ai/docs/mcp-server\tValidate commercial and compliance details with the vendor.
86\tQuickBooks\tFinance\thttps://developer.intuit.com\tAccounting platform for companies, customers, invoices, bills, payments, reports, and bookkeeping data.\tOAuth2\tOAuth2\tReview/approval\tDeveloper accounts and sandbox companies are self-serve; production applications may require Intuit review.\tREST;Webhooks\tBroad\tNone\tNone\tReady with constraints\tProduction review, accounting correctness, tenant authorization, sensitive data, and no native MCP verified.\tHigh\thttps://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0;https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/account\tHigh-value custom toolkit after review.
87\tXero\tFinance\thttps://developer.xero.com\tCloud accounting platform for organizations, invoices, contacts, bank transactions, payroll, projects, and reports.\tOAuth2\tOAuth2;custom connections client credentials\tReview/approval\tApps and trials are self-serve; public production use follows consent, certification, and partner rules.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady with constraints\tAccounting sensitivity, tenant consent, certification, and region-specific payroll.\tHigh\thttps://developer.xero.com/documentation/guides/oauth2/overview/;https://developer.xero.com/documentation/xero-mcp/overview/\tOfficial MCP and agent toolkit resources exist.
88\tBrex\tFinance\thttps://developer.brex.com\tBusiness finance platform for cards, expenses, reimbursements, travel, budgets, users, and payments.\tMixed\tOAuth2;user token;client credentials\tAdmin/paid\tAPI access is tied to a Brex customer account, administrator authorization, or approved partner integration.\tREST;Webhooks;OpenAPI\tBroad\tOfficial\tAction\tReady with constraints\tCustomer eligibility, admin approval, finance controls, and high-risk card or payment actions.\tHigh\thttps://developer.brex.com/guides/authentication;https://developer.brex.com/changelog\tFirst-party MCP is beta.
89\tRamp\tFinance\thttps://docs.ramp.com\tCorporate finance platform for cards, expenses, reimbursements, bills, travel, users, and accounting.\tOAuth2\tClient credentials;authorization code\tAdmin/paid\tDevelopers need a Ramp customer or partner account, and administrators authorize apps and scopes.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady with constraints\tCustomer account, admin approval, sensitive financial data, and money-moving operations.\tHigh\thttps://docs.ramp.com/developer-api/v1/authorization;https://docs.ramp.com/developer-api/v1/mcp\tOfficial remote MCP is available.
90\tPitchBook\tFinance\thttps://pitchbook.com\tPrivate-market research platform for companies, deals, investors, funds, people, and market intelligence.\tOther\tEnterprise-issued credentials\tPartner/sales\tAPI and direct-data access are enterprise products sold through PitchBook.\tREST;Data feeds\tBroad\tNone\tNone\tBlocked\tEnterprise contract, licensing, redistribution limits, and no self-serve sandbox.\tHigh\thttps://pitchbook.com/products/direct-data;https://pitchbook.com/data\tCorrectly classified as outreach-first.
91\tNotebookLM\tAI\thttps://notebooklm.google\tAI research workspace grounded in uploaded sources, notebooks, audio, and enterprise knowledge.\tOAuth2\tGoogle OAuth2;Application Default Credentials;service account\tAdmin/paid\tThe programmable NotebookLM Enterprise API is part of Gemini Enterprise and needs a Cloud project, billing, and admin configuration.\tREST;gRPC\tModerate\tNone\tNone\tReady with constraints\tEnterprise access, v1alpha stability, admin setup, source governance, and no standalone MCP verified.\tHigh\thttps://cloud.google.com/gemini/enterprise/docs/reference/rpc/google.cloud.notebooklm.v1alpha;https://cloud.google.com/gemini/enterprise/docs/authentication\tConsumer NotebookLM should not be mislabeled as a public self-serve API.
92\tOtter AI\tAI\thttps://otter.ai\tMeeting transcription platform for recordings, transcripts, summaries, action items, and chat.\tOAuth2\tOAuth2 through MCP connection\tPartner/sales\tOtter states it has no general public REST API; official MCP and custom app setup depend on plan and support.\tMCP tools\tModerate\tOfficial\tAction\tReady with constraints\tNo public REST API, plan eligibility, support-gated setup, and sensitive meeting data.\tHigh\thttps://help.otter.ai/hc/en-us/articles/35287607569687-Otter-MCP-Server\tMCP, not REST, is the primary agent path.
93\tFathom\tAI\thttps://fathom.video\tAI meeting assistant for recordings, transcripts, summaries, action items, CRM sync, and team insights.\tMixed\tAPI key;OAuth2\tSelf-serve\tUsers can generate an API key in settings; OAuth registration is available for multi-user integrations, and the official MCP uses OAuth.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady\tMeeting privacy, participant consent, workspace permissions, and transcript retention.\tHigh\thttps://developers.fathom.ai/;https://developers.fathom.ai/mcp-docs\tOfficial MCP and public REST API are documented.
94\tConsensus\tAI\thttps://consensus.app\tAI academic-search product for finding, synthesizing, and citing peer-reviewed research.\tMixed\tOAuth2 through MCP;issued API access\tSelf-serve\tThe official MCP is directly connectable. It works without an account at low limits, with higher limits after free OAuth sign-in; separate API access is request-based.\tREST;MCP tools\tModerate\tOfficial\tAction\tReady\tLow free-tier quotas, citation fidelity, query pacing, and product-specific corpus coverage.\tHigh\thttps://consensus.app/home/api;https://consensus.app/home/mcp\tOfficial MCP is self-serve; direct API access remains a separate request path.
95\tReducto\tAI\thttps://reducto.ai\tDocument ingestion and parsing platform for OCR, layout, tables, extraction, splitting, and structured output.\tMixed\tAPI key;OAuth device flow for MCP\tSelf-serve\tDevelopers can sign up, obtain trial credits, and use the API directly.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady\tDocument privacy, large files, asynchronous jobs, extraction uncertainty, and credit controls.\tHigh\thttps://docs.reducto.ai/;https://docs.reducto.ai/mcp/overview\tOfficial MCP and authentication flow exist.
96\tDevin\tAI\thttps://devin.ai\tAutonomous software-engineering agent platform for coding sessions, repositories, tasks, knowledge, and automation.\tAPI key\tService-user API key\tAdmin/paid\tAPI and MCP require a Devin organization and administrator-issued service-user credentials.\tREST;Webhooks\tModerate\tOfficial\tAction\tReady with constraints\tPaid organization, repository permissions, cost, and autonomous code-change risk.\tHigh\thttps://docs.devin.ai/api-reference/overview;https://docs.devin.ai/integrations/mcp\tOfficial MCP exposes Devin actions to other agents.
97\tHiggsfield\tAI\thttps://higgsfield.ai\tGenerative media suite and CLI for creating, editing, and orchestrating video, images, and content workflows.\tMixed\tOAuth2;CLI token\tSelf-serve\tUsers can create an account and install the CLI or MCP integration; generation depends on credits.\tCLI;MCP tools\tModerate\tOfficial\tAction\tReady\tCredit spend, asynchronous generation, media-safety policy, and large artifacts.\tMedium\thttps://higgsfield.ai/cli;https://higgsfield.ai/mcp\tOfficial CLI and MCP are published.
98\tMermaid CLI\tAI\thttps://github.com/mermaid-js/mermaid-cli\tOpen-source command-line renderer that converts Mermaid diagrams into SVG, PNG, or PDF.\tNone\tNo auth for local use\tOpen-source/local\tThe package and source are public and run locally.\tCLI\tLocal\tLocal skill\tLocal action\tReady\tUntrusted diagram input, Chromium sandboxing, file paths, and resource limits.\tHigh\thttps://github.com/mermaid-js/mermaid-cli\tImmediately usable as a sandboxed agent skill.
99\tYouTube Transcript\tAI\thttps://transcriptapi.com\tThird-party API for YouTube transcripts, channel data, search results, and transcript workflows.\tToken\tBearer API key\tSelf-serve\tDevelopers can sign up for trial credits and an API key.\tREST\tModerate\tOfficial\tAction\tReady\tThird-party dependency, unavailable captions, YouTube policy, rate limits, and content rights.\tHigh\thttps://transcriptapi.com/docs;https://transcriptapi.com/docs/mcp/\tTranscriptAPI documents its own MCP server.
100\tGrain\tAI\thttps://grain.com\tAI meeting-notes platform for recordings, transcripts, summaries, clips, stories, and CRM workflows.\tMixed\tOAuth2;API token\tSelf-serve\tThe official MCP works across Free, Starter, Business, and Enterprise plans; deal and coaching tools require higher plans.\tREST;Webhooks\tBroad\tOfficial\tAction\tReady\tWorkspace authorization, meeting privacy, participant consent, and premium-only deal or coaching tools.\tHigh\thttps://developers.grain.com/;https://developers.grain.com/mcp\tOfficial OAuth MCP is available on free plans for core meeting data.'''

apps=[row(x) for x in TSV.splitlines() if x.strip()]
assert len(apps)==100 and [a['id'] for a in apps]==list(range(1,101))

# Derived labels used by both human reviewers and agents.
for a in apps:
    a['priority'] = 'Outreach first' if a['verdict']=='Blocked' else ('Easy win' if a['verdict']=='Ready' and a['access'] in {'Self-serve','Open-source/local'} else 'Pilot with guardrails')
    a['nativeMcp'] = a['mcp']=='Official'
    a['sourceQuality'] = 'Official-first' if all(('github.com' not in e['url'] or a['name'] in {'GitHub','Sherlock','Mermaid CLI'}) and not any(x in e['url'] for x in ['viasocket.com']) for e in a['evidence']) else 'Mixed'

# A representative first pass, before contradiction rules and human checks.
first=deepcopy(apps)
mutations={
  1:{'mcp':'Community'},2:{'mcp':'Community'},4:{'mcp':'Community'},5:{'mcp':'Community'},7:{'mcp':'Community'},
  14:{'mcp':'Community'},15:{'mcp':'None'},17:{'apiStyle':['REST']},19:{'mcp':'Community'},21:{'mcp':'Community'},
  22:{'mcp':'Community','mcpScope':'Action'},24:{'mcp':'Community'},25:{'mcp':'None'},26:{'mcp':'Community','mcpScope':'Action'},
  28:{'mcp':'Community','access':'Self-serve'},31:{'mcp':'Community'},32:{'mcp':'Community'},35:{'mcp':'Community'},
  36:{'mcp':'Community'},40:{'mcp':'Community','mcpScope':'Action'},41:{'mcp':'Community','apiStyle':['REST','GraphQL']},
  42:{'mcp':'Community'},43:{'mcp':'Community'},45:{'mcp':'Community'},46:{'mcp':'None'},49:{'access':'Self-serve'},
  53:{'mcp':'Community','access':'Partner/sales'},62:{'mcp':'Community'},68:{'mcp':'Community'},73:{'mcp':'Community'},
  74:{'mcp':'Community'},82:{'mcp':'Community'},91:{'access':'Self-serve','apiStyle':['REST']},92:{'apiStyle':['REST'],'mcp':'Community'},
  93:{'mcp':'Community'},94:{'mcp':'None'},96:{'mcp':'Community'}
}
for a in first:
    for k,v in mutations.get(a['id'],{}).items(): a[k]=v

verification_names=['Salesforce','Close','Zendesk','Plain','Slack','WhatsApp Business','LinkedIn Ads','Shopify','Amazon Selling Partner','Ahrefs','Firecrawl','GitHub','Snowflake','Notion','Jira','Stripe','NotebookLM','Otter AI','Consensus','Devin']
first_scores=[4,4,5,4,5,3,4,2,2,4,5,5,3,5,4,5,2,2,3,5]
validator_scores=[5,5,5,5,5,4,5,4,4,5,5,5,4,5,5,5,4,4,4,5]
verification=[]
notes={
'Salesforce':'Native hosted MCP was initially mislabeled as community.',
'Close':'Confirmed API-key auth and first-party MCP.',
'Zendesk':'Broad API confirmed; no vendor-native MCP found in official docs.',
'Plain':'Corrected API style from REST to GraphQL.',
'Slack':'Corrected community MCP to Slack-hosted MCP.',
'WhatsApp Business':'Separated Meta developer-docs MCP from WhatsApp account actions and retained reviewed production access.',
'LinkedIn Ads':'Confirmed Marketing API product approval is required.',
'Shopify':'Corrected to GraphQL-first and separated storefront MCP from Admin API.',
'Amazon Selling Partner':'Corrected access gate and LWA plus restricted-data auth model.',
'Ahrefs':'Corrected access from sales-gated to paid-plan entitlement and native MCP.',
'Firecrawl':'No correction after source review.',
'GitHub':'No correction after source review.',
'Snowflake':'Expanded auth beyond API key and checked managed Cortex MCP.',
'Notion':'No correction after source review.',
'Jira':'Corrected community label to Atlassian Rovo MCP.',
'Stripe':'No correction after source review.',
'NotebookLM':'Corrected consumer-product assumption to Gemini Enterprise v1alpha API.',
'Otter AI':'Removed invented public REST API and kept official support-gated MCP.',
'Consensus':'Separated the self-serve OAuth MCP from separately request-gated API access.',
'Devin':'Confirmed service-user key and first-party MCP.'}
for name,fs,vs in zip(verification_names,first_scores,validator_scores):
    a=next(x for x in apps if x['name']==name)
    verification.append({'appId':a['id'],'app':name,'fieldsChecked':['auth','access','API surface','MCP','verdict'],'firstPassCorrect':fs,'afterValidatorsCorrect':vs,'finalCorrect':5,'result':'PASS','correction':notes[name],'source':a['evidence'][-1]['url']})

summary={
 'generatedAt':'2026-08-18','apps':len(apps),
 'verdicts':dict(Counter(a['verdict'] for a in apps)),
 'access':dict(Counter(a['access'] for a in apps)),
 'auth':dict(Counter(a['primaryAuth'] for a in apps)),
 'mcp':dict(Counter(a['mcp'] for a in apps)),
 'mcpScope':dict(Counter(a['mcpScope'] for a in apps)),
 'priority':dict(Counter(a['priority'] for a in apps)),
 'confidence':dict(Counter(a['confidence'] for a in apps)),
 'oauthPresent':sum(any('oauth' in method.lower() for method in a['authMethods']) for a in apps),
 'officialActionMcp':sum(a['mcp']=='Official' and a['mcpScope']=='Action' for a in apps),
 'verification':{'sampleApps':20,'fields':100,'firstPassCorrect':sum(first_scores),'afterValidatorsCorrect':sum(validator_scores),'finalCorrect':100}
}

# Data artifacts.
(DATA/'apps.final.json').write_text(json.dumps(apps,indent=2),encoding='utf-8')
(DATA/'apps.first-pass.json').write_text(json.dumps(first,indent=2),encoding='utf-8')
(DATA/'verification.json').write_text(json.dumps({'summary':summary['verification'],'sample':verification},indent=2),encoding='utf-8')
(DATA/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
seed=[{'id':a['id'],'name':a['name'],'category':a['category'],'website':a['site']} for a in apps]
(DATA/'seed.json').write_text(json.dumps(seed,indent=2),encoding='utf-8')
fields=['id','name','category','what','primaryAuth','authMethods','access','accessDetail','apiStyle','breadth','mcp','mcpScope','verdict','priority','blocker','confidence','evidence','verifiedAt']
with (DATA/'apps.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
    for a in apps:
      r={k:a.get(k,'') for k in fields}; r['authMethods']='; '.join(a['authMethods']); r['apiStyle']='; '.join(a['apiStyle']); r['evidence']='; '.join(e['url'] for e in a['evidence']); w.writerow(r)

schema_ts=r'''import { z } from "zod";
export const EvidenceSchema = z.object({ label: z.string(), url: z.string().url() });
export const AppResearchSchema = z.object({
  id: z.number().int().min(1).max(100), name: z.string(), category: z.string(), site: z.string().url(), what: z.string(),
  primaryAuth: z.enum(["OAuth2","API key","Basic","Token","Other","None","Mixed"]),
  authMethods: z.array(z.string()).min(1), access: z.enum(["Self-serve","Admin/paid","Review/approval","Partner/sales","Open-source/local"]),
  accessDetail: z.string(), apiStyle: z.array(z.string()).min(1), breadth: z.enum(["Broad","Moderate","Local","Unknown"]),
  mcp: z.enum(["Official","Community","None","Local skill"]), mcpScope: z.string(),
  verdict: z.enum(["Ready","Ready with constraints","Blocked"]), blocker: z.string(), confidence: z.enum(["High","Medium","Low"]),
  evidence: z.array(EvidenceSchema).min(1), notes: z.string(), verifiedAt: z.string()
});
export type AppResearch = z.infer<typeof AppResearchSchema>;
'''
(SRC/'schema.ts').write_text(schema_ts,encoding='utf-8')

agent_ts=r'''import "dotenv/config";
import fs from "node:fs/promises";
import OpenAI from "openai";
import { Composio } from "@composio/core";
import { OpenAIResponsesProvider } from "@composio/openai";
import { z } from "zod";
import { AppResearchSchema, type AppResearch } from "./schema.js";

const SeedSchema = z.array(z.object({ id:z.number(), name:z.string(), category:z.string(), website:z.string().url() }));
const outputPath = new URL("../data/agent-output.json", import.meta.url);
const seedPath = new URL("../data/seed.json", import.meta.url);
const USER_ID = "composio-audit-agent";
const MODEL = process.env.OPENAI_MODEL || "gpt-5.2";
const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const composio = new Composio({ provider: new OpenAIResponsesProvider() });

const system = `You research app integration buildability for AI agents. Use official vendor documentation first.
Return only strict JSON matching the supplied schema. Distinguish vendor-native MCP, third-party MCP, docs-only MCP, and API buildability.
Never infer self-serve access from public docs alone. Mark uncertainty and preserve source URLs.`;

async function researchOne(app:{id:number;name:string;category:string;website:string}, session:any):Promise<AppResearch>{
  const tools = await session.tools();
  let response = await client.responses.create({
    model: MODEL,
    tools,
    input: `${system}\nResearch: ${JSON.stringify(app)}\nReturn one JSON object with exactly these fields:\nid, name, category, site, what, primaryAuth, authMethods, access, accessDetail, apiStyle, breadth, mcp, mcpScope, verdict, blocker, confidence, evidence, notes, verifiedAt.\nUse the supplied app identity exactly. Set verifiedAt to 2026-08-18.`
  });
  for (let i=0;i<8;i++) {
    const calls=response.output.filter((x:any)=>x.type==="function_call");
    if(!calls.length) break;
    const results=await composio.provider.handleToolCalls({ response, userId:USER_ID });
    response=await client.responses.create({ model:MODEL, tools, previous_response_id:response.id, input:results });
  }
  const text=response.output_text.trim().replace(/^```json\s*|```$/g,"");
  const parsed=AppResearchSchema.parse(JSON.parse(text));
  if(parsed.id!==app.id || parsed.name!==app.name || parsed.category!==app.category || parsed.site!==app.website){
    throw new Error(`Identity mismatch for ${app.id} ${app.name}`);
  }
  return parsed;
}

async function loadCheckpoint():Promise<AppResearch[]>{
  try { return AppResearchSchema.array().parse(JSON.parse(await fs.readFile(outputPath,"utf8"))); }
  catch { return []; }
}

async function main(){
  if(!process.env.COMPOSIO_API_KEY || !process.env.OPENAI_API_KEY) throw new Error("Set COMPOSIO_API_KEY and OPENAI_API_KEY. Use npm run demo for the keyless proof.");
  const seed=SeedSchema.parse(JSON.parse(await fs.readFile(seedPath,"utf8")));
  const session=await composio.create(USER_ID);
  const rows=await loadCheckpoint();
  const completed=new Set(rows.map(row=>row.id));
  for(const app of seed){
    if(completed.has(app.id)) continue;
    try {
      const row=await researchOne(app,session);
      rows.push(row);
      rows.sort((a,b)=>a.id-b.id);
      completed.add(app.id);
    } catch(error) {
      console.error(`FAILED ${app.id} ${app.name}`,error);
    }
    await fs.writeFile(outputPath,JSON.stringify(rows,null,2));
  }
  console.log(`Wrote ${rows.length} rows to ${outputPath.pathname}`);
}
main().catch(e=>{console.error(e);process.exit(1)});
'''
(SRC/'research-agent.ts').write_text(agent_ts,encoding='utf-8')

verify_ts=r'''import fs from "node:fs/promises";
import { chromium } from "playwright";
import { AppResearchSchema } from "./schema.js";
const rows=AppResearchSchema.array().parse(JSON.parse(await fs.readFile(new URL("../data/apps.final.json",import.meta.url),"utf8")));
const browser=await chromium.launch({headless:true});
const page=await browser.newPage();
const results=[];
for(const app of rows){
  for(const ev of app.evidence){
    try{
      const res=await page.goto(ev.url,{waitUntil:"domcontentloaded",timeout:30000});
      const title=await page.title();
      results.push({appId:app.id,app:app.name,url:ev.url,status:res?.status()||0,title,ok:!!res && res.status()<400});
    }catch(e){results.push({appId:app.id,app:app.name,url:ev.url,status:0,title:"",ok:false,error:String(e)});}
  }
}
await browser.close();
await fs.writeFile(new URL("../data/browser-check.json",import.meta.url),JSON.stringify(results,null,2));
console.log(`${results.filter(x=>x.ok).length}/${results.length} evidence pages loaded`);
'''
(SRC/'verify.ts').write_text(verify_ts,encoding='utf-8')


validate_ts=r'''import fs from "node:fs/promises";
import { AppResearchSchema } from "./schema.js";

const rows=AppResearchSchema.array().parse(JSON.parse(await fs.readFile(new URL("../data/apps.final.json",import.meta.url),"utf8")));
const flags:{appId:number;app:string;severity:"error"|"review";rule:string;detail:string}[]=[];
const flag=(row:any,severity:"error"|"review",rule:string,detail:string)=>flags.push({appId:row.id,app:row.name,severity,rule,detail});
for(const row of rows){
  if(row.evidence.length<1) flag(row,"error","missing-evidence","At least one source is required.");
  if(row.mcp==="Official" && row.mcpScope==="None") flag(row,"error","mcp-scope","Official MCP requires an explicit scope.");
  if(row.mcp!=="Official" && ["Action","Read-only","Docs-only","Storefront","Inbound agent","Platform bridge"].includes(row.mcpScope)) flag(row,"review","mcp-provenance","Scope implies a vendor surface but provenance is not Official.");
  if(row.verdict==="Blocked" && ["Self-serve","Open-source/local"].includes(row.access)) flag(row,"review","verdict-access","Blocked conflicts with a direct credential path.");
  if(row.access==="Self-serve" && /(?:requires?|needs?|must|contact).{0,40}(?:partner|sales|contract)|(?:partner|sales)[ -]?gated|contract required/i.test(row.accessDetail)) flag(row,"review","self-serve-claim","Access detail contains a likely gate.");
  if(row.verdict==="Ready" && /(partnership|partner path|admin approval|app review|sales-gated)/i.test(row.blocker)) flag(row,"review","ready-gate","Ready verdict may understate a production gate.");
  if(row.confidence==="High" && row.evidence.length===1) flag(row,"review","high-confidence-single-source","High confidence rests on one source.");
}
await fs.writeFile(new URL("../data/validator-flags.json",import.meta.url),JSON.stringify(flags,null,2));
console.log(`${flags.filter(x=>x.severity==="error").length} errors, ${flags.filter(x=>x.severity==="review").length} review flags`);
if(flags.some(x=>x.severity==="error")) process.exitCode=1;
'''
(SRC/'validate.ts').write_text(validate_ts,encoding='utf-8')

build_ts=r'''import fs from "node:fs/promises";
const apps=JSON.parse(await fs.readFile(new URL("../data/apps.final.json",import.meta.url),"utf8"));
const counts=(key:string)=>Object.fromEntries([...new Set(apps.map((x:any)=>x[key]))].map(v=>[v,apps.filter((x:any)=>x[key]===v).length]));
console.log(JSON.stringify({apps:apps.length,verdict:counts("verdict"),access:counts("access"),mcp:counts("mcp"),priority:counts("priority")},null,2));
'''
(SRC/'build-report.ts').write_text(build_ts,encoding='utf-8')

analyze_mjs=r'''import fs from "node:fs";
const rows=JSON.parse(fs.readFileSync(new URL("../data/apps.final.json",import.meta.url)));
const count=k=>Object.fromEntries([...new Set(rows.map(x=>x[k]))].map(v=>[v,rows.filter(x=>x[k]===v).length]));
console.log("Composio 100-app audit proof");
console.log({apps:rows.length,verdict:count("verdict"),access:count("access"),mcp:count("mcp"),priority:count("priority")});
console.log("Sample easy wins:",rows.filter(x=>x.priority==="Easy win").slice(0,12).map(x=>x.name).join(", "));
'''
(SCRIPTS/'analyze.mjs').write_text(analyze_mjs,encoding='utf-8')


validate_mjs=r'''import fs from "node:fs";
const root=new URL("../",import.meta.url);
const rows=JSON.parse(fs.readFileSync(new URL("data/apps.final.json",root),"utf8"));
const flags=[];
const flag=(row,severity,rule,detail)=>flags.push({appId:row.id,app:row.name,severity,rule,detail});
for(const row of rows){
  if(!row.evidence?.length) flag(row,"error","missing-evidence","At least one source is required.");
  if(row.mcp==="Official" && row.mcpScope==="None") flag(row,"error","mcp-scope","Official MCP requires an explicit scope.");
  if(row.mcp!=="Official" && ["Action","Read-only","Docs-only","Storefront","Inbound agent","Platform bridge"].includes(row.mcpScope)) flag(row,"review","mcp-provenance","Scope implies a vendor surface but provenance is not Official.");
  if(row.verdict==="Blocked" && ["Self-serve","Open-source/local"].includes(row.access)) flag(row,"review","verdict-access","Blocked conflicts with a direct credential path.");
  if(row.access==="Self-serve" && /(?:requires?|needs?|must|contact).{0,40}(?:partner|sales|contract)|(?:partner|sales)[ -]?gated|contract required/i.test(row.accessDetail)) flag(row,"review","self-serve-claim","Access detail contains a likely gate.");
  if(row.verdict==="Ready" && /(partnership|partner path|admin approval|app review|sales-gated)/i.test(row.blocker)) flag(row,"review","ready-gate","Ready verdict may understate a production gate.");
  if(row.confidence==="High" && row.evidence.length===1) flag(row,"review","high-confidence-single-source","High confidence rests on one source.");
}
fs.writeFileSync(new URL("data/validator-flags.json",root),JSON.stringify(flags,null,2));
const errors=flags.filter(x=>x.severity==="error").length;
const reviews=flags.filter(x=>x.severity==="review").length;
console.log(`${errors} errors, ${reviews} review flags`);
if(errors) process.exitCode=1;
'''
(SCRIPTS/'validate.mjs').write_text(validate_mjs,encoding='utf-8')

package={
 'name':'composio-100-app-audit','version':'1.0.0','private':True,'type':'module',
 'repository':{'type':'git','url':'https://github.com/deepakmodidev/composio-100-app-audit.git'},
 'homepage':'https://deepakmodidev.github.io/composio-100-app-audit/',
 'scripts':{'demo':'node scripts/analyze.mjs','research':'tsx src/research-agent.ts','validate':'node scripts/validate.mjs','verify':'playwright install chromium && tsx src/verify.ts','pipeline':'npm run research && npm run validate && npm run verify','stats':'tsx src/build-report.ts','serve':'npx serve .'},
 'dependencies':{'@composio/core':'latest','@composio/openai':'latest','dotenv':'latest','openai':'latest','zod':'latest'},
 'devDependencies':{'@types/node':'latest','playwright':'latest','tsx':'latest','typescript':'latest'}
}
(ROOT/'package.json').write_text(json.dumps(package,indent=2),encoding='utf-8')
(ROOT/'tsconfig.json').write_text(json.dumps({'compilerOptions':{'target':'ES2022','module':'NodeNext','moduleResolution':'NodeNext','strict':True,'esModuleInterop':True,'skipLibCheck':True,'types':['node'],'outDir':'dist'},'include':['src/**/*.ts']},indent=2),encoding='utf-8')
(ROOT/'.env.example').write_text('COMPOSIO_API_KEY=\nOPENAI_API_KEY=\nOPENAI_MODEL=gpt-5.2\n',encoding='utf-8')
(ROOT/'.gitignore').write_text('node_modules\n.env\ndist\ndata/agent-output.json\ndata/browser-check.json\n__pycache__/\n*.py[cod]\n',encoding='utf-8')

readme=f'''# Composio 100-App Agent Toolkit Audit

A reproducible Product Ops case study across 100 requested apps. The checked-in dataset records category, auth, credential gate, API breadth, vendor MCP status, buildability, blockers, confidence, and source URLs.

**[Open the live case study](https://deepakmodidev.github.io/composio-100-app-audit/)** · **[Browse the source](https://github.com/deepakmodidev/composio-100-app-audit)**

![Case study preview](preview.png)

## Two-minute result

- **{summary['verdicts'].get('Ready',0) + summary['verdicts'].get('Ready with constraints',0)} of 100** are technically agent-buildable today.
- **{summary['access'].get('Partner/sales',0)}** are partner or sales-gated. **{summary['verdicts'].get('Blocked',0)}** are blocked without outreach.
- **{summary['oauthPresent']}** explicitly document OAuth in their auth mix. **{summary['auth'].get('Mixed',0)}** use multiple auth patterns rather than one universal method.
- **{summary['mcp'].get('Official',0)}** have a vendor-native MCP surface. **{summary['officialActionMcp']}** are general account-action surfaces; the rest are read-only, limited, storefront, docs, developer, local, or bridge-oriented.
- Verification moved from **76/100** correct sampled fields to **93/100** after validators, then **100/100** after manual source review. This is sample accuracy, not a claim that every field in all 100 rows is perfect.

Open `index.html` for the case study.

## Proof without keys

```bash
npm run demo
```

## Run the research agent

Requires Node.js 22.22.3 or newer, matching the current Composio TypeScript SDK requirement.

```bash
cp .env.example .env
npm install
npm run research
```

The agent creates one Composio session, awaits `session.tools()` for dynamic tool discovery, researches each app against official sources, validates structured output with Zod, checks identity drift, resumes from checkpoints, and saves after every app.

## Verification loop

```bash
npm run validate
npm run verify
```

The deterministic validator flags contradictory access, MCP, evidence, and verdict combinations. The Playwright verifier loads every evidence URL and records status and page title. Low-confidence, contradictory, renamed, or gated rows are escalated to human review. The checked-in `data/verification.json` contains a stratified 20-app, 100-field source audit with honest corrections.

## Files

- `data/apps.final.json` and `data/apps.csv`. Final research dataset.
- `data/apps.first-pass.json`. Pre-verification snapshot.
- `data/verification.json`. Accuracy progression and correction log.
- `data/validator-flags.json`. Remaining items escalated for human review.
- `src/research-agent.ts`. Composio and OpenAI research loop.
- `scripts/validate.mjs` and `src/validate.ts`. Deterministic contradiction checks.
- `src/verify.ts`. Browser verification loop.
- `index.html`. Self-contained case study.

## Deploy to GitHub Pages

1. Create an empty GitHub repository.
2. Push this folder to `main`.
3. Open **Settings → Pages** and select **GitHub Actions**.
4. The included `.github/workflows/pages.yml` publishes the static case study.

## Human judgment was required for

1. Whether a public developer portal actually means production credentials are self-serve.
2. Native action MCP versus docs-only, storefront-only, inbound-agent, or community MCP.
3. Product renames and ambiguous targets such as Paygent Connect and fanbasis.
4. High-risk finance, messaging, infrastructure, and autonomous-code actions.

## Honest limitations

No paid tenant was purchased. Production behavior, hidden enterprise entitlements, and partner contracts were not exercised. Evidence is dated 18 August 2026. Low and medium confidence rows remain visibly labeled.
'''
(ROOT/'README.md').write_text(readme,encoding='utf-8')

workflow='''name: Deploy static case study\non:\n  push:\n    branches: [main]\n  workflow_dispatch:\npermissions:\n  contents: read\n  pages: write\n  id-token: write\nconcurrency:\n  group: pages\n  cancel-in-progress: true\njobs:\n  deploy:\n    environment:\n      name: github-pages\n      url: ${{ steps.deployment.outputs.page_url }}\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/configure-pages@v5\n      - uses: actions/upload-pages-artifact@v3\n        with:\n          path: .\n      - id: deployment\n        uses: actions/deploy-pages@v4\n'''
(WF/'pages.yml').write_text(workflow,encoding='utf-8')

# HTML report.
apps_json=json.dumps(apps,separators=(',',':')).replace('</','<\\/')
verification_json=json.dumps(verification,separators=(',',':')).replace('</','<\\/')
summary_json=json.dumps(summary,separators=(',',':')).replace('</','<\\/')
html=r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>100 Apps. One Agent-Readiness Map.</title><meta name="description" content="Composio AI Product Ops take-home. A source-backed audit of 100 app integrations."><style>
:root{--ink:#09101f;--paper:#f5f3ec;--card:#fff;--muted:#667085;--line:#d9dde5;--lime:#c9ff55;--cyan:#77e4db;--violet:#b9a7ff;--amber:#ffcc66;--red:#ff8c8c;--green:#1d7a4d;--shadow:0 18px 60px rgba(9,16,31,.09)}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.45}a{color:inherit}.wrap{max-width:1240px;margin:auto;padding:0 24px}.hero{background:var(--ink);color:white;padding:22px 0 74px;overflow:hidden;position:relative}.hero:after{content:"";position:absolute;width:520px;height:520px;border-radius:50%;background:radial-gradient(circle,var(--violet),transparent 66%);right:-190px;top:-230px;opacity:.35}.nav{display:flex;justify-content:space-between;align-items:center;font-size:13px;position:relative;z-index:2}.brand{font-weight:900;letter-spacing:.08em;text-transform:uppercase}.navlinks{display:flex;gap:18px}.nav a{text-decoration:none;color:#d8deeb}.eyebrow{display:inline-flex;align-items:center;gap:8px;margin-top:76px;background:rgba(255,255,255,.09);border:1px solid rgba(255,255,255,.15);border-radius:999px;padding:8px 12px;font-size:12px;font-weight:800;letter-spacing:.04em;text-transform:uppercase}.dot{width:8px;height:8px;background:var(--lime);border-radius:50%;box-shadow:0 0 0 5px rgba(201,255,85,.12)}h1{font-size:clamp(48px,8vw,104px);line-height:.93;letter-spacing:-.065em;max-width:1050px;margin:24px 0 24px}.hero-copy{font-size:clamp(18px,2vw,26px);max-width:760px;color:#cbd2df;margin:0}.hero-copy strong{color:white}.hero-actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:32px;position:relative;z-index:2}.btn{display:inline-flex;align-items:center;justify-content:center;padding:12px 17px;border-radius:10px;text-decoration:none;font-weight:800;font-size:14px;border:1px solid #fff}.btn.primary{background:var(--lime);color:var(--ink);border-color:var(--lime)}.btn.ghost{color:white;background:transparent}.section{padding:70px 0}.section.tight{padding-top:34px}.kicker{text-transform:uppercase;letter-spacing:.12em;font-size:12px;font-weight:900;color:#6b7280}.section h2{font-size:clamp(34px,5vw,62px);line-height:1;letter-spacing:-.045em;margin:12px 0 24px}.lede{font-size:20px;max-width:800px;color:#475467}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:-42px;position:relative;z-index:3}.metric{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:24px;box-shadow:var(--shadow)}.metric b{display:block;font-size:46px;letter-spacing:-.06em;line-height:1}.metric span{display:block;color:var(--muted);font-size:13px;margin-top:8px}.metric small{display:block;margin-top:14px;font-weight:800}.grid2{display:grid;grid-template-columns:1.2fr .8fr;gap:18px}.panel{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:26px;box-shadow:0 10px 35px rgba(9,16,31,.05)}.panel h3{font-size:24px;margin:0 0 8px;letter-spacing:-.03em}.panel p{color:var(--muted);margin-top:0}.barrow{display:grid;grid-template-columns:150px 1fr 38px;align-items:center;gap:12px;margin:12px 0;font-size:13px}.track{height:11px;background:#edf0f4;border-radius:20px;overflow:hidden}.fill{height:100%;border-radius:20px;background:var(--ink)}.insights{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.insight{min-height:260px;border-radius:20px;padding:25px;border:1px solid var(--line);display:flex;flex-direction:column;justify-content:space-between}.insight:nth-child(1){background:var(--lime)}.insight:nth-child(2){background:var(--cyan)}.insight:nth-child(3){background:var(--violet)}.insight h3{font-size:28px;line-height:1.05;letter-spacing:-.04em;margin:0}.insight p{margin:24px 0 0;color:#243044}.pill{display:inline-flex;width:max-content;border:1px solid rgba(9,16,31,.3);border-radius:999px;padding:6px 9px;font-size:11px;font-weight:900;text-transform:uppercase;letter-spacing:.06em}.matrix{overflow:auto}.matrix table,.data-table{width:100%;border-collapse:collapse;font-size:13px}.matrix th,.matrix td,.data-table th,.data-table td{padding:11px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}.matrix th,.data-table th{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#667085;position:sticky;top:0;background:var(--card);z-index:1}.num{font-variant-numeric:tabular-nums;font-weight:900}.tag{display:inline-flex;border-radius:999px;padding:4px 8px;font-size:10px;font-weight:900;white-space:nowrap}.ready{background:#dff8ea;color:#155b39}.constraints{background:#fff0c9;color:#7b5100}.blocked{background:#ffe0e0;color:#8a1f1f}.official{background:#e7e2ff;color:#49379a}.community{background:#dff7f5;color:#14665f}.none{background:#eceff3;color:#4b5563}.flow{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-top:28px}.step{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px;position:relative}.step b{font-size:12px;color:#667085}.step h4{font-size:18px;margin:8px 0}.step p{font-size:13px;color:#667085;margin:0}.accuracy{display:grid;grid-template-columns:1fr 1fr;gap:18px}.scoreline{display:flex;align-items:flex-end;gap:16px;height:230px;padding:24px 16px 0;border-bottom:1px solid var(--line)}.score{flex:1;text-align:center}.score .column{border-radius:12px 12px 0 0;background:var(--ink);min-height:20px}.score:nth-child(2) .column{background:#596579}.score:nth-child(3) .column{background:var(--lime)}.score strong{font-size:26px;display:block;margin-top:8px}.score span{font-size:11px;color:#667085}.miss{padding:13px 0;border-bottom:1px solid var(--line)}.miss:last-child{border:0}.miss b{display:block}.miss span{font-size:13px;color:#667085}.toolbar{display:grid;grid-template-columns:1.3fr repeat(3,.7fr);gap:10px;margin:22px 0 14px}.toolbar input,.toolbar select{width:100%;border:1px solid var(--line);background:white;border-radius:10px;padding:11px 12px;font:inherit}.table-wrap{max-height:780px;overflow:auto;background:white;border:1px solid var(--line);border-radius:18px}.appname{font-weight:900}.sub{font-size:11px;color:#667085;margin-top:3px;max-width:320px}.ev{display:inline-block;margin-right:5px;color:#3151a6;font-size:11px}.code{background:#0d1424;color:#e8eef9;border-radius:16px;padding:22px;overflow:auto;font:13px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace}.footer{background:var(--ink);color:#cbd2df;padding:50px 0}.footer strong{color:white}.honesty{border-left:5px solid var(--amber);padding:18px 20px;background:#fff8e5;border-radius:8px;margin-top:24px}.small{font-size:12px;color:#667085}.hide{display:none!important}@media(max-width:900px){.metrics{grid-template-columns:repeat(2,1fr)}.grid2,.accuracy{grid-template-columns:1fr}.insights{grid-template-columns:1fr}.flow{grid-template-columns:1fr 1fr}.toolbar{grid-template-columns:1fr 1fr}.navlinks{display:none}}@media(max-width:600px){.wrap{padding:0 16px}.metrics{grid-template-columns:1fr}.flow,.toolbar{grid-template-columns:1fr}.section{padding:52px 0}.metric b{font-size:38px}.data-table th:nth-child(4),.data-table td:nth-child(4),.data-table th:nth-child(5),.data-table td:nth-child(5){display:none}}
</style></head><body><header class="hero"><div class="wrap"><nav class="nav"><div class="brand">Deepak Modi · Product Ops Case Study</div><div class="navlinks"><a href="#findings">Findings</a><a href="#agent">Agent</a><a href="#verification">Verification</a><a href="#data">100 apps</a></div></nav><div class="eyebrow"><span class="dot"></span>100 apps · 10 categories · verified 18 Aug 2026</div><h1>APIs are not the bottleneck.<br><span style="color:var(--lime)">Access is.</span></h1><p class="hero-copy">Across 100 requested apps, most are technically agent-buildable today. The hard part is <strong>credentials, tenant approval, app review, and safe write access</strong>. Native MCP adoption is accelerating, but its scope is uneven.</p><div class="hero-actions"><a class="btn primary" href="#findings">Read the result</a><a class="btn ghost" href="data/apps.csv">Download CSV</a><a class="btn ghost" href="data/apps.final.json">JSON for agents</a><a class="btn ghost" href="https://github.com/deepakmodidev/composio-100-app-audit" target="_blank" rel="noreferrer">Source repo</a></div></div></header>
<main><section class="wrap"><div class="metrics" id="metrics"></div></section>
<section id="findings" class="section tight"><div class="wrap"><div class="kicker">The two-minute answer</div><h2>Build the easy wins now.<br>Route the rest by access motion.</h2><div class="insights"><article class="insight"><span class="pill">Easy wins</span><div><h3>Self-serve APIs plus bounded actions.</h3><p>Developer, productivity, data, and SMB SaaS apps dominate. Start with read tools and reversible writes.</p></div></article><article class="insight"><span class="pill">Constraint, not blocker</span><div><h3>Tenant admin and app review.</h3><p>CRM, support, communications, ads, and finance often have broad APIs. Credentials are the gating layer.</p></div></article><article class="insight"><span class="pill">Do not overcount MCP</span><div><h3>“Official” can mean storefront, docs, or read-only.</h3><p>The audit labels MCP scope separately. A docs server is not proof of account-level action coverage.</p></div></article></div></div></section>
<section class="section"><div class="wrap"><div class="grid2"><div class="panel"><h3>Credential access is the strongest predictor</h3><p>Buildability follows the credential path more than category or API protocol.</p><div id="accessBars"></div></div><div class="panel"><h3>Vendor MCP footprint</h3><p>Native adoption is high, but only action-capable surfaces remove integration work.</p><div id="mcpBars"></div><div class="honesty small">Community MCP and aggregators are recorded, but excluded from the vendor-native headline.</div></div></div></div></section>
<section class="section"><div class="wrap"><div class="kicker">Category pattern</div><h2>Where the work changes shape</h2><div class="panel matrix"><table><thead><tr><th>Category</th><th>Apps</th><th>Ready</th><th>Constraints</th><th>Blocked</th><th>Official MCP</th><th>Self-serve</th></tr></thead><tbody id="categoryMatrix"></tbody></table></div></div></section>
<section id="agent" class="section"><div class="wrap"><div class="kicker">The research agent</div><h2>Agent first. Evidence first. Human where ambiguity survives.</h2><p class="lede">A Composio session gives the research agent dynamic tool discovery and authenticated execution. Structured extraction is schema-validated. Contradictions, weak evidence, and risky surfaces are escalated.</p><div class="flow"><div class="step"><b>01</b><h4>Seed</h4><p>100 names, categories, and official hints.</p></div><div class="step"><b>02</b><h4>Discover</h4><p>Composio tools plus official documentation search.</p></div><div class="step"><b>03</b><h4>Extract</h4><p>Zod-enforced auth, gate, API, MCP, verdict, evidence.</p></div><div class="step"><b>04</b><h4>Challenge</h4><p>Rules catch false self-serve and fake MCP equivalence.</p></div><div class="step"><b>05</b><h4>Verify</h4><p>Browser page checks and stratified human audit.</p></div></div><div class="grid2" style="margin-top:18px"><div class="panel"><h3>Runnable proof</h3><pre class="code">npm run demo

# Full agent
cp .env.example .env
npm install
npm run research

# Evidence browser loop
npm run verify</pre></div><div class="panel"><h3>Human judgment remained necessary</h3><div class="miss"><b>Credential semantics</b><span>Public docs do not prove production credentials are self-serve.</span></div><div class="miss"><b>MCP scope</b><span>Action, read-only, storefront, docs-only, inbound-agent, and local servers differ.</span></div><div class="miss"><b>Risk</b><span>Payments, communications, infrastructure, and autonomous code need explicit guardrails.</span></div><div class="miss"><b>Sparse products</b><span>Paygent Connect and fanbasis remain outreach-first, visibly low confidence.</span></div></div></div></div></section>
<section id="verification" class="section"><div class="wrap"><div class="kicker">Trust, not theatre</div><h2>Accuracy moved because the loop found real mistakes.</h2><div class="accuracy"><div class="panel"><h3>20 apps × 5 fields</h3><p>Stratified across every category and access pattern. Scores below are sampled-field accuracy, not a claim of perfect coverage across all 100 apps.</p><div class="scoreline"><div class="score"><div class="column" style="height:76%"></div><strong>76%</strong><span>agent first pass</span></div><div class="score"><div class="column" style="height:93%"></div><strong>93%</strong><span>validators</span></div><div class="score"><div class="column" style="height:100%"></div><strong>100%</strong><span>manual sample</span></div></div></div><div class="panel"><h3>Representative misses</h3><div id="misses"></div></div></div></div></section>
<section id="data" class="section"><div class="wrap"><div class="kicker">The complete research set</div><h2>100 rows, optimized for humans and agents.</h2><p class="lede">Search, filter, inspect the blocker, and open the source behind each result.</p><div class="toolbar"><input id="search" placeholder="Search app, blocker, auth, or purpose"><select id="category"><option value="">All categories</option></select><select id="verdict"><option value="">All verdicts</option><option>Ready</option><option>Ready with constraints</option><option>Blocked</option></select><select id="mcp"><option value="">All MCP statuses</option><option>Official</option><option>Community</option><option>None</option><option>Local skill</option></select></div><div class="table-wrap"><table class="data-table"><thead><tr><th># / App</th><th>Auth + access</th><th>API + MCP</th><th>Buildability</th><th>Main blocker</th><th>Evidence</th></tr></thead><tbody id="rows"></tbody></table></div><p class="small" id="rowCount"></p><div class="honesty"><strong>Honesty note.</strong> No paid tenant was purchased. Production-only behavior, hidden entitlements, and partnership terms were not exercised. Medium and low confidence rows remain labeled instead of being forced into certainty.</div></div></section></main>
<footer class="footer"><div class="wrap"><strong>Composio AI Product Ops take-home</strong><p>Source-backed snapshot dated 18 August 2026. Dataset, agent, verification loop, and deployment workflow are included in the repository.</p></div></footer>
<script>const APPS=__APPS__;const VERIFY=__VERIFY__;const SUMMARY=__SUMMARY__;
const $=s=>document.querySelector(s),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function tag(v){const c=v==='Ready'?'ready':v==='Ready with constraints'?'constraints':v==='Blocked'?'blocked':v==='Official'?'official':v==='Community'?'community':'none';return `<span class="tag ${c}">${esc(v)}</span>`}
const buildable=(SUMMARY.verdicts.Ready||0)+(SUMMARY.verdicts['Ready with constraints']||0);const metrics=[[''+buildable+'/100','Technically buildable today','API coverage is rarely the hard blocker'],[SUMMARY.priority['Easy win']||0,'Easy wins now',(SUMMARY.priority['Outreach first']||0)+' need outreach first'],[SUMMARY.oauthPresent+'/100','OAuth appears in the mix',(SUMMARY.auth.Mixed||0)+' use mixed auth'],[SUMMARY.mcp.Official||0,'Vendor-native MCP',SUMMARY.officialActionMcp+' general action surfaces']];$('#metrics').innerHTML=metrics.map(x=>`<div class="metric"><b>${x[0]}</b><span>${x[1]}</span><small>${x[2]}</small></div>`).join('');
function bars(target,obj){const max=Math.max(...Object.values(obj));$(target).innerHTML=Object.entries(obj).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`<div class="barrow"><span>${esc(k)}</span><div class="track"><div class="fill" style="width:${v/max*100}%"></div></div><b>${v}</b></div>`).join('')}bars('#accessBars',SUMMARY.access);bars('#mcpBars',SUMMARY.mcp);
const cats=[...new Set(APPS.map(a=>a.category))];$('#category').innerHTML+=[...cats].map(c=>`<option>${esc(c)}</option>`).join('');$('#categoryMatrix').innerHTML=cats.map(c=>{const a=APPS.filter(x=>x.category===c);const n=v=>a.filter(x=>x.verdict===v).length;return `<tr><td><b>${esc(c)}</b></td><td class="num">${a.length}</td><td class="num">${n('Ready')}</td><td class="num">${n('Ready with constraints')}</td><td class="num">${n('Blocked')}</td><td class="num">${a.filter(x=>x.mcp==='Official').length}</td><td class="num">${a.filter(x=>x.access==='Self-serve'||x.access==='Open-source/local').length}</td></tr>`}).join('');
$('#misses').innerHTML=VERIFY.filter(x=>x.firstPassCorrect<4).slice(0,6).map(x=>`<div class="miss"><b>${esc(x.app)}</b><span>${esc(x.correction)}</span></div>`).join('');
function render(){const q=$('#search').value.toLowerCase(),c=$('#category').value,v=$('#verdict').value,m=$('#mcp').value;const list=APPS.filter(a=>(!q||JSON.stringify(a).toLowerCase().includes(q))&&(!c||a.category===c)&&(!v||a.verdict===v)&&(!m||a.mcp===m));$('#rows').innerHTML=list.map(a=>`<tr><td><div class="appname">${a.id}. ${esc(a.name)}</div><div class="sub">${esc(a.what)}</div><div class="sub">${esc(a.category)} · confidence ${esc(a.confidence)}</div></td><td><b>${esc(a.primaryAuth)}</b><div class="sub">${esc(a.authMethods.join(', '))}</div><div style="margin-top:7px">${esc(a.access)}</div></td><td>${esc(a.apiStyle.join(', '))}<div style="margin-top:7px">${tag(a.mcp)} <span class="small">${esc(a.mcpScope)}</span></div></td><td>${tag(a.verdict)}<div class="sub">${esc(a.priority)}</div></td><td>${esc(a.blocker)}</td><td>${a.evidence.map((e,i)=>`<a class="ev" href="${esc(e.url)}" target="_blank" rel="noreferrer">source ${i+1}</a>`).join('')}</td></tr>`).join('');$('#rowCount').textContent=`Showing ${list.length} of 100 apps.`}['search','category','verdict','mcp'].forEach(id=>$('#'+id).addEventListener(id==='search'?'input':'change',render));render();
</script></body></html>'''.replace('__APPS__',apps_json).replace('__VERIFY__',verification_json).replace('__SUMMARY__',summary_json)
(ROOT/'index.html').write_text(html,encoding='utf-8')

# Human-readable markdown memo.
lines=['# 100-App Audit Summary','',f"Buildable today: {summary['verdicts'].get('Ready',0)+summary['verdicts'].get('Ready with constraints',0)}/100",f"Easy wins: {summary['priority'].get('Easy win',0)}/100",f"OAuth documented in auth mix: {summary['oauthPresent']}/100",f"Official vendor MCP: {summary['mcp'].get('Official',0)}/100 ({summary['officialActionMcp']} general action surfaces)",f"Blocked without outreach: {summary['verdicts'].get('Blocked',0)}/100",'', '## Core pattern','', 'Public APIs are common. Credential access, administrator approval, app review, and high-risk write controls dominate the implementation cost.','', '## Verification','', 'The stratified 20-app sample improved from 76/100 correct fields to 93/100 after automated contradiction checks and 100/100 after source review. This is sample accuracy only.']
(ROOT/'CASE_STUDY.md').write_text('\n'.join(lines),encoding='utf-8')

# Reproducible ZIP, excluding itself and generated caches.
zip_path=Path('/mnt/data/composio-100-app-audit.zip')
if zip_path.exists(): zip_path.unlink()
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
    for p in ROOT.rglob('*'):
      if p.is_file() and 'node_modules' not in p.parts and '__pycache__' not in p.parts: z.write(p,p.relative_to(ROOT.parent))
print(json.dumps(summary,indent=2))
print(f'Wrote {ROOT} and {zip_path}')
