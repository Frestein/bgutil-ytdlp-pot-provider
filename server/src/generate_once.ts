import { SessionManager, YoutubeSessionDataCaches } from "./session_manager";
import { Command } from "@commander-js/extra-typings";
import * as fs from "fs";
import * as path from "path";

// Follow XDG Base Directory Specification: https://specifications.freedesktop.org/basedir-spec/latest/
let cachedir;
if ("XDG_CACHE_HOME" in process.env) {
    cachedir = path.resolve(
        process.env.XDG_CACHE_HOME || "",
        "bgutil-ytdlp-pot-provider",
    );
} else if ("HOME" in process.env) {
    cachedir = path.resolve(
        process.env.HOME || "",
        ".cache",
        "bgutil-ytdlp-pot-provider",
    );
} else {
    // fall back to a known path if environment variables are not found
    cachedir = path.resolve(__dirname, "..");
}
if (!fs.existsSync(cachedir)) {
    fs.mkdir(cachedir, { recursive: true }, (err) => {
        if (err) throw err;
    });
}
const CACHE_PATH = path.resolve(cachedir, "cache.json");

const program = new Command()
    .option("-v, --visitor-data <visitordata>")
    .option("-d, --data-sync-id <data-sync-id>")
    .option("-p, --proxy <proxy-all>")
    .option("--verbose");

program.parse();
const options = program.opts();

(async () => {
    const visitorData = options.visitorData;
    const dataSyncId = options.dataSyncId;
    const proxy = options.proxy || "";
    const verbose = options.verbose || false;
    let visitIdentifier: string;
    const cache: YoutubeSessionDataCaches = {};
    if (fs.existsSync(CACHE_PATH)) {
        try {
            const parsedCaches = JSON.parse(
                fs.readFileSync(CACHE_PATH, "utf8"),
            );
            for (const visitIdentifier in parsedCaches) {
                const parsedCache = parsedCaches[visitIdentifier];
                if (parsedCache) {
                    cache[visitIdentifier] = {
                        poToken: parsedCache.poToken,
                        generatedAt: new Date(parsedCache.generatedAt),
                        visitIdentifier,
                    };
                }
            }
        } catch (e) {
            console.warn(`Error parsing cache. e = ${e}`);
        }
    }

    const sessionManager = new SessionManager(verbose, cache);
    function log(msg: string) {
        if (verbose) console.log(msg);
    }

    if (dataSyncId) {
        log(`Received request for data sync ID: '${dataSyncId}'`);
        visitIdentifier = dataSyncId;
    } else if (visitorData) {
        log(`Received request for visitor data: '${visitorData}'`);
        visitIdentifier = visitorData;
    } else {
        log(`Received request for visitor data, grabbing from Innertube`);
        const generatedVisitorData = await sessionManager.generateVisitorData();
        if (!generatedVisitorData) process.exit(1);
        log(`Generated visitor data: ${generatedVisitorData}`);
        visitIdentifier = generatedVisitorData;
    }

    try {
        const sessionData = await sessionManager.generatePoToken(
            visitIdentifier,
            proxy,
        );

        try {
            fs.writeFileSync(
                CACHE_PATH,
                JSON.stringify(
                    sessionManager.getYoutubeSessionDataCaches(true),
                ),
                "utf8",
            );
        } catch (e) {
            console.warn(
                `Error writing cache. err.name = ${e.name}. err.message = ${e.message}. err.stack = ${e.stack}`,
            );
        } finally {
            console.log(JSON.stringify(sessionData));
        }
    } catch (e) {
        console.error(
            `Failed while generating POT. err.name = ${e.name}. err.message = ${e.message}. err.stack = ${e.stack}`,
        );
        console.log(JSON.stringify({}));
        process.exit(1);
    }
})();
